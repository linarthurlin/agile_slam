"""Pure control contracts; timestamps passed here are monotonic receipt times."""
import math


def clamp(value,low,high):
    return max(low,min(high,value))


class SpeedController:
    def __init__(self,config):
        self.config=config
        self.received=None
        self.target=0.
        self.angle=0.
        self.integral=0.
        self.last=None

    def command(self,speed,yaw_rate,now):
        if not all(math.isfinite(v) for v in (speed,yaw_rate,now)) or speed<0:
            self.received=None
            self.target=self.angle=0.
            self.integral=0.
            return False
        self.target=clamp(speed,0.,self.config['max_speed'])
        self.angle=clamp(math.atan(self.config['wheelbase']*yaw_rate/speed),-self.config['max_steer'],self.config['max_steer']) if speed>=.05 else 0.
        self.received=now
        return True

    def step(self,now,speed,report_age,enabled,inhibited):
        dt=clamp(now-self.last,0.,.1) if self.last is not None else 0.
        self.last=now
        fresh=self.received is not None and 0<=now-self.received<=self.config['command_timeout']
        usable=math.isfinite(speed) and 0<=report_age<=self.config['report_timeout'] and enabled and not inhibited
        target=self.target if fresh and usable else 0.
        if not usable or not fresh or target<.01:
            self.integral=0.
            return 0.,.4,self.angle if usable else 0.,'tracking' if fresh and usable else 'inhibited'
        error=target-speed
        self.integral=clamp(self.integral+error*dt,-.3,.3)
        effort=2.*error+.4*self.integral+self.config['mock_drag']*target/self.config['mock_accel_gain']
        if effort>=0:
            return clamp(effort,0.,.65),0.,self.angle,'tracking'
        return 0.,clamp(-effort,0.,.75),self.angle,'tracking'


class MockState:
    def __init__(self):
        self.enabled=False
        self.fault=False
        self.override=False
        self.timeout=False
        self.gear=2
        self.velocity=0.
        self.angle=0.

    def enable(self,requested,ready):
        if not requested:
            self.enabled=False
            return True
        if not ready or self.fault or self.override:
            return False
        self.timeout=False
        self.enabled=True
        return True

    def trip(self,reason):
        self.enabled=False
        if reason=='fault':self.fault=True
        if reason=='override':self.override=True
        if reason=='timeout':self.timeout=True

    def shift(self,gear,speed):
        if gear not in (0,2,3) or not math.isfinite(speed):
            self.trip('fault')
            return False
        if gear!=self.gear and abs(speed)>.05:
            self.trip('fault')
            return False
        self.gear=gear
        return True

    def advance(self,dt,accel,brake,shaft,rate,ready,config):
        if not all(math.isfinite(v) for v in (dt,accel,brake,shaft,rate)) or not 0<=accel<=1 or not 0<=brake<=1 or rate<0 or abs(shaft)>config['max_steer']*config['steering_ratio']+1e-6 or (accel>.001 and brake>.001):
            self.trip('fault')
        if not ready and self.enabled:self.trip('timeout')
        if not self.enabled or self.gear!=3:
            self.velocity=0.
            return 0.,self.angle
        dt=clamp(dt,0.,.1)
        limit=min(rate,config['steering_rate'])/config['steering_ratio']
        self.angle+=clamp(shaft/config['steering_ratio']-self.angle,-limit*dt,limit*dt)
        acceleration=config['mock_accel_gain']*accel-config['mock_brake_gain']*brake-config['mock_drag']*self.velocity
        self.velocity=clamp(self.velocity+acceleration*dt,0.,config['max_speed']+.05)
        return self.velocity,self.angle


class CommandBundle:
    """Commit a coherent accelerator/brake/steering cycle across ROS topics."""
    def __init__(self):
        self.pending={}
        self.last_stamp=None
    def push(self,key,stamp,value):
        if self.last_stamp is not None and stamp<self.last_stamp:return None
        self.pending[key]=(stamp,value)
        keys=('accel','brake','steer')
        if not all(k in self.pending and self.pending[k][0]==stamp for k in keys):return None
        self.last_stamp=stamp
        return {k:self.pending[k][1] for k in keys}
    def reset(self):
        self.pending.clear();self.last_stamp=None
