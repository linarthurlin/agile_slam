"""Pure geometry helpers for the inherited simulation vehicle."""
import math


def curvature_from_front_angles(left, right, wheelbase, track):
    tl, tr = math.tan(left), math.tan(right)
    return 0.5 * (tl / (wheelbase + track * tl / 2) + tr / (wheelbase - track * tr / 2))


def steering_from_twist(speed, yaw_rate, wheelbase, limit):
    if abs(speed) < 0.05:
        return 0.0
    return max(-limit, min(limit, math.atan(wheelbase * yaw_rate / speed)))


def integrate(x, y, yaw, speed, yaw_rate, dt):
    if abs(yaw_rate) < 1e-9:
        return x + speed * dt * math.cos(yaw), y + speed * dt * math.sin(yaw), yaw
    next_yaw = yaw + yaw_rate * dt
    radius = speed / yaw_rate
    return x + radius * (math.sin(next_yaw)-math.sin(yaw)), y - radius * (math.cos(next_yaw)-math.cos(yaw)), next_yaw


def footprint_overlaps_box(x, y, yaw, center, size):
    """SAT overlap for a conservative body footprint and an axis-aligned box."""
    c,s=math.cos(yaw),math.sin(yaw)
    body=[(x+c*px-s*py,y+s*px+c*py) for px,py in ((-1.5,-.8),(1.6,-.8),(1.6,.8),(-1.5,.8))]
    bx,by=center
    sx,sy=size[:2]
    box=[(bx+dx*sx/2,by+dy*sy/2) for dx,dy in ((-1,-1),(1,-1),(1,1),(-1,1))]
    for ax,ay in ((1,0),(0,1),(c,s),(-s,c)):
        a=[px*ax+py*ay for px,py in body]
        b=[px*ax+py*ay for px,py in box]
        if max(a)<min(b) or max(b)<min(a):
            return False
    return True


def footprint_overlaps_polygon(x, y, yaw, polygon):
    """SAT overlap with a convex static obstacle footprint."""
    c,s=math.cos(yaw),math.sin(yaw)
    body=[(x+c*px-s*py,y+s*px+c*py) for px,py in ((-1.5,-.8),(1.6,-.8),(1.6,.8),(-1.5,.8))]
    axes=[(c,s),(-s,c)]
    axes.extend((-(b[1]-a[1]),b[0]-a[0]) for a,b in zip(polygon,polygon[1:]+polygon[:1]))
    for ax,ay in axes:
        a=[px*ax+py*ay for px,py in body]
        b=[px*ax+py*ay for px,py in polygon]
        if max(a)<min(b) or max(b)<min(a):return False
    return True
