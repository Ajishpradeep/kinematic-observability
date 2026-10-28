"""Independent two-link geometry. Positions in metres, angles in radians."""
import math
import torch


def lengths(p):
    return torch.linalg.vector_norm(p[..., 1:, :] - p[..., :-1, :], dim=-1)


def bend(p):
    d = torch.nn.functional.normalize(p[..., 1:, :] - p[..., :-1, :], dim=-1)
    return torch.acos((d[..., 0, :] * d[..., 1, :]).sum(-1).clamp(-1 + 1e-10, 1 - 1e-10))


def basis(az, el):
    d = torch.stack((torch.cos(el)*torch.cos(az), torch.cos(el)*torch.sin(az), torch.sin(el)), -1)
    a = torch.stack((-torch.sin(az), torch.cos(az), torch.zeros_like(az)), -1)
    b = torch.linalg.cross(d, a)
    return d, a, b


def encode(p):
    d = torch.nn.functional.normalize(p[..., 1, :] - p[..., 0, :], dim=-1)
    e = torch.nn.functional.normalize(p[..., 2, :] - p[..., 1, :], dim=-1)
    az = torch.atan2(d[..., 1], d[..., 0])
    el = torch.atan2(d[..., 2], torch.linalg.vector_norm(d[..., :2], dim=-1))
    _, a, b = basis(az, el)
    beta = torch.atan2((e*b).sum(-1), (e*a).sum(-1))
    return torch.cat((p[..., 0, :], torch.stack((az, el, beta, bend(p)), -1)), -1)


def fk(q, lens, cap=None):
    root, az, el, beta, angle = q[..., :3], q[..., 3], q[..., 4], q[..., 5], q[..., 6]
    if cap is not None:
        angle = cap * torch.sigmoid(angle)
    d, a, b = basis(az, el)
    e = torch.cos(angle)[..., None]*d + torch.sin(angle)[..., None]*(torch.cos(beta)[..., None]*a + torch.sin(beta)[..., None]*b)
    middle = root + lens[..., 0, None]*d
    end = middle + lens[..., 1, None]*e
    return torch.stack((root, middle, end), -2)


def project(p, K, dist):
    """OpenCV pinhole with k1,k2,p1,p2,k3 distortion; no hidden alignment."""
    z = p[..., 2].clamp_min(0.05)
    x, y = p[..., 0]/z, p[..., 1]/z
    r2 = x*x+y*y
    k1,k2,p1,p2,k3 = [dist[..., i, None] for i in range(5)]
    radial = 1+k1*r2+k2*r2*r2+k3*r2*r2*r2
    xd = x*radial+2*p1*x*y+p2*(r2+2*x*x)
    yd = y*radial+p1*(r2+2*y*y)+2*p2*x*y
    return torch.stack((K[..., 0,0,None]*xd+K[..., 0,2,None], K[..., 1,1,None]*yd+K[..., 1,2,None]), -1)


def refine(initial, lens, uv, weight, K, dist, method, steps=200, cap_deg=150):
    """Matched per-frame MAP-like refinement; tether and weights are uncalibrated."""
    if method == 'raw':
        return initial.clone()
    q0 = encode(initial)
    if method == 'length_project':
        return fk(q0, lens)
    cartesian = method == 'cartesian_reprojection'
    hard = method == 'fk_hard'
    cap = math.radians(cap_deg)
    q = initial.clone() if cartesian else q0.clone()
    if hard:
        q[...,6] = torch.logit((q[...,6]/cap).clamp(1e-4,1-1e-4))
    q.requires_grad_(True)
    opt = torch.optim.Adam([q], lr=0.02)
    for _ in range(steps):
        p = q if cartesian else fk(q,lens,cap if hard else None)
        prior = ((p-initial)/0.08).square().sum((-1,-2))
        repro = (((project(p,K,dist)-uv)/5).square().sum(-1)*weight).sum(-1)
        loss = prior + (0 if method == 'fk_prior' else repro)
        if method == 'fk_soft':
            penalty = torch.relu(bend(p)-cap)/math.radians(10)
            loss = loss + penalty.square()
        loss = loss + 1e4*torch.relu(0.05-p[...,2]).square().sum(-1)
        opt.zero_grad()
        loss.sum().backward()
        opt.step()
    out = q if cartesian else fk(q,lens,cap if hard else None)
    if not torch.isfinite(out).all():
        raise RuntimeError('Nonfinite refined pose')
    return out.detach()


def metrics(p, truth, lens, uv, weight, K, dist):
    err = torch.linalg.vector_norm(p-truth, dim=-1)*1000
    pixel = torch.linalg.vector_norm(project(p,K,dist)-uv,dim=-1)
    visible = weight > 0
    return {
        'joint_mm':err.mean(-1), 'distal_mm':err[...,2],
        'distal_depth_mm':(p[...,2,2]-truth[...,2,2]).abs()*1000,
        'bend_deg':(bend(p)-bend(truth)).abs()*180/math.pi,
        'reprojection_px':(pixel*visible).sum(-1)/visible.sum(-1).clamp_min(1),
        'length_reference_mm':(lengths(p)-lengths(truth)).abs().mean(-1)*1000,
        'length_constraint_mm':(lengths(p)-lens).abs().mean(-1)*1000,
    }
