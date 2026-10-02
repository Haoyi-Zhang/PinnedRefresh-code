"""Input and certificate boundary checks. No generated case import side effects."""
from __future__ import annotations
import copy, unittest
from src.model import validate
from src.producer import produce
from src.checker import verify

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tr={"field":5,"threshold":2,"epochs":2,"observations":[{"kind":"snapshot","epoch":0,"x":1}]}
    def test_empty(self):
        t=copy.deepcopy(self.tr); t['observations']=[]
        self.assertTrue(verify(t,produce(t)))
    def test_composite_field(self):
        t=copy.deepcopy(self.tr);t['field']=9
        with self.assertRaises(ValueError): validate(t)
    def test_zero_coordinate(self):
        t=copy.deepcopy(self.tr);t['observations'][0]['x']=0
        with self.assertRaises(ValueError): validate(t)
    def test_boolean_not_integer(self):
        t=copy.deepcopy(self.tr);t['threshold']=True
        with self.assertRaises(ValueError): validate(t)
    def test_bad_epoch(self):
        t=copy.deepcopy(self.tr);t['observations'][0]['epoch']=2
        with self.assertRaises(ValueError): validate(t)
    def test_reversed_delta(self):
        t=copy.deepcopy(self.tr);t['observations']=[{'kind':'delta','before':1,'after':0,'x':1}]
        with self.assertRaises(ValueError): validate(t)
    def test_unknown_field(self):
        t=copy.deepcopy(self.tr);t['assume_secure']=True
        with self.assertRaises(ValueError): validate(t)
    def test_observation_limit(self):
        t=copy.deepcopy(self.tr);t['observations']*=65
        with self.assertRaises(ValueError): validate(t)
    def test_certificate_noncanonical(self):
        c=produce(self.tr);c['polynomials'][0][1]+=5
        self.assertFalse(verify(self.tr,c))
    def test_certificate_boolean(self):
        c=produce(self.tr);c['polynomials'][0][0]=True
        self.assertFalse(verify(self.tr,c))
    def test_certificate_extra_field(self):
        c=produce(self.tr);c['proof']='trust me'
        self.assertFalse(verify(self.tr,c))
    def test_wrong_certificate_shape(self):
        self.assertFalse(verify(self.tr,{'kind':'revealing','weights':[]}))
    def test_missing_certificate(self):
        self.assertFalse(verify(self.tr,{}))
    def test_mutated_hiding(self):
        c=produce(self.tr);c['polynomials'][0][1]=(c['polynomials'][0][1]+1)%5
        self.assertFalse(verify(self.tr,c))
    def test_mutated_revealing(self):
        t=copy.deepcopy(self.tr);t['observations'].append({'kind':'snapshot','epoch':0,'x':2})
        c=produce(t);self.assertTrue(verify(t,c));c['weights'][0]=(c['weights'][0]+1)%5
        self.assertFalse(verify(t,c))
    def test_no_producer_import_in_checker(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/'src/checker.py').read_text()
        self.assertNotIn('from .producer import',source)
        self.assertNotIn('import producer',source)

if __name__=='__main__': unittest.main()
