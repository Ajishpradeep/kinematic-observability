import unittest
import torch
from geometry import encode, fk, lengths, project, refine

torch.set_default_dtype(torch.float64)

class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.q=torch.tensor([[0.1,0.2,3.,0.7,0.2,-0.8,1.2]])
        self.l=torch.tensor([[0.3,0.25]])

    def test_round_trip_and_lengths(self):
        p=fk(self.q,self.l)
        torch.testing.assert_close(fk(encode(p),self.l),p,atol=1e-12,rtol=1e-12)
        torch.testing.assert_close(lengths(p),self.l,atol=1e-12,rtol=1e-12)

    def test_jacobian(self):
        self.assertTrue(torch.autograd.gradcheck(lambda q:fk(q,self.l), (self.q.requires_grad_(),)))

    def test_depth_ambiguity(self):
        # Root at z=3, distal ray x/z=.1. Both ray/sphere intersections have length .5.
        z=torch.tensor([(6-(36-4*1.01*8.75)**.5)/(2*1.01), (6+(36-4*1.01*8.75)**.5)/(2*1.01)])
        p=torch.stack((.1*z,torch.zeros_like(z),z),-1)
        torch.testing.assert_close(torch.linalg.vector_norm(p-torch.tensor([0.,0.,3.]),dim=-1),torch.full((2,),.5))
        uv=project(p[None],torch.eye(3)[None],torch.zeros(1,5))[0]
        torch.testing.assert_close(uv[0],uv[1])
        self.assertGreater(float(abs(z[0]-z[1])),.5)

    def test_refinement_identity(self):
        p=fk(self.q,self.l)
        K=torch.tensor([[[1200.,0,960],[0,1200,540],[0,0,1.]]])
        d=torch.zeros(1,5); uv=project(p,K,d)
        out=refine(p,self.l,uv,torch.ones(1,3),K,d,'fk_soft',steps=1)
        torch.testing.assert_close(out,p,atol=1e-5,rtol=1e-5)

    def test_hard_bound(self):
        from geometry import bend
        q=self.q.clone(); q[:,6]=100
        p=fk(q,self.l,cap=1.5)
        self.assertLessEqual(float(bend(p)[0]),1.5+1e-8)

if __name__=='__main__': unittest.main()
