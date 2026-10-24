import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from semantic_review import validate
from model_backend import validate_packet


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.record={'id':'chat:test','source':'chat','date':'2030-01-01','author':'Contributor 01','body':'I supplied the screen. Another contributor supplied extraction.','parent':None,'links':[],'title':'Synthetic check'}
        self.review={'account':'A shared implementation.','claims':[{'id':'C1','category':'contribution','statement':'Contributor 01 supplied the screen.','limits':'Extraction was supplied by another contributor.','evidence':[{'record_id':'chat:test','quote':'I supplied the screen.'}]}],'unknowns':[],'rejected_conclusions':[]}

    def test_exact_quotes_receive_offsets_and_hashes(self):
        result=validate(self.review,[self.record])
        self.assertTrue(result['valid'])
        self.assertEqual(result['claims'][0]['evidence'][0]['start'],0)
        self.assertFalse(result['meaning_validated'])

    def test_invented_quotation_fails(self):
        self.review['claims'][0]['evidence'][0]['quote']='I built everything.'
        self.assertFalse(validate(self.review,[self.record])['valid'])

    def test_correct_quote_does_not_prove_overclaim(self):
        self.review['claims'][0]['statement']='Contributor 01 built everything.'
        result=validate(self.review,[self.record])
        self.assertTrue(result['valid'])
        self.assertFalse(result['meaning_validated'])

    def test_duplicate_and_empty_claims_fail(self):
        self.review['claims'].append(copy.deepcopy(self.review['claims'][0]))
        self.assertFalse(validate(self.review,[self.record])['valid'])
        self.review['claims']=[]
        # Empty output is schema-valid but cannot earn recall points.
        self.assertEqual(validate(self.review,[self.record])['quote_count'],0)

    def test_packet_does_not_accept_evaluator_or_arbitrary_fields(self):
        packet={'synthetic':True,'question':'Test','records':[self.record],'scope':{},'retrieval_limits':[]}
        validate_packet(packet)
        packet['answer_key']=['Do not send this']
        with self.assertRaises(ValueError):validate_packet(packet)

if __name__=='__main__':unittest.main()
