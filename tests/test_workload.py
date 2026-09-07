import hashlib, json, unittest
from workload import ProjectionService

class WorkloadTests(unittest.TestCase):
    def test_independent_projection(self):
        rows=[[x%7-3 for x in range(i*16,(i+1)*16)] for i in range(8)]
        columns=[[((k*8+j)%5)-2 for k in range(16)] for j in range(8)]
        expected=[float(sum(x*y for x,y in zip(row,col))) for row in rows for col in columns]
        result=ProjectionService().handle('test')
        self.assertEqual(result['result_sha256'],hashlib.sha256(json.dumps(expected).encode()).hexdigest())

if __name__=='__main__': unittest.main()
