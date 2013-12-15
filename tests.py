import icomradio
import unittest

class TestRadioControl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = icomradio.IcomRadio(0x58, '/dev/ttyO2') 

    def test_freq(self):
        self.assertEqual(self.r.set_freq('0146750000'), 'FB')
        self.assertEqual(self.r.set_freq('0469999999'), 'FB')
        self.assertEqual(self.r.set_freq('0010110000'), 'FB')
        self.assertEqual(self.r.set_freq('001010000'), 'FF')
        self.assertEqual(self.r.set_freq('!0a0100t0'), 'FF')
    
    def test_vfo_mem(self):
        self.assertRegex(self.r.set_vfo('A'), '[0-9]{4} [0-9]{10}')
        self.assertRegex(self.r.set_vfo('B'), '[0-9]{4} [0-9]{10}')
        self.assertEqual(self.r.set_vfo('C'), 'FF')
        self.assertEqual(self.r.set_vfo('1'), 'FF')
        self.assertEqual(self.r.set_vfo('#'), 'FF')
        self.assertEqual(self.r.set_mem('99'), 'FB')
        self.assertEqual(self.r.set_mem('50'), 'FB')
        self.assertEqual(self.r.set_mem('02'), 'FB')
        self.assertEqual(self.r.set_mem('9'),  'FF')
        self.assertEqual(self.r.set_mem('199'), 'FF')
    
    def test_scn(self):
        self.assertEqual(self.r.scan_start(), 'FB')
        f = self.r.scan_stop()
        self.assertRegex(f, '[0-9]{10}')
    
    def test_mode(self):
        self.assertEqual(self.r.set_mode('CW'), 'FB')
        self.assertEqual(self.r.set_mode('USB'), 'FB')
        self.assertEqual(self.r.set_mode('LSB'), 'FB')
        self.assertEqual(self.r.set_mode('CW-N'), 'FB')
        self.assertEqual(self.r.set_mode('RTTY'), 'FB')
        self.assertEqual(self.r.set_mode('FM'), 'FB')
        self.assertEqual(self.r.set_mode('AM'), 'FB')
        self.assertEqual(self.r.set_mode('WFM'), 'FB')
        self.assertEqual(self.r.set_mode('asdf'), 'FF')
    
    def test_read_freq(self):
        f = self.r.read_freq()
        self.assertRegex(f, '[0-9]{10}')
    
    def test_read_mode(self):
        self.r.set_mode('WFM')
        self.assertEqual(self.r.read_mode(), '0601')
        self.r.set_mode('CW')
        self.assertEqual(self.r.read_mode(), '0301')
    
    def test_read_att(self):
        self.r.set_patt('ATT')
        self.assertEqual(self.r.read_att(), '20')
        self.r.set_patt('PRE')
        self.assertEqual(self.r.read_att(), '00')
        self.r.set_patt('OFF')
        self.assertEqual(self.r.read_att(), '00')
    
    def test_read_meter(self):
        self.r.set_mode('WFM')
        self.r.set_freq('0000300000')
        m = self.r.read_meter()
        self.assertRegex(m, '[0-9]{4}')

    def test_patt(self):
        self.assertTrue(self.r.set_patt('a'), 'FB')
        self.assertTrue(self.r.set_patt('p'), 'FB')
        self.assertTrue(self.r.set_patt('o'), 'FB')
        self.assertTrue(self.r.set_patt('x'), 'FF')

    def test_agc(self):
        self.assertTrue(self.r.set_agc('FAST'), 'FB')
        self.assertTrue(self.r.set_agc('SLOW'), 'FB')
        self.assertTrue(self.r.set_agc('x'), 'FF')
        self.assertTrue(self.r.set_agc('F'), 'FF')
        
if __name__ == '__main__':
    unittest.main()

