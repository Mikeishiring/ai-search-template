"""Contact metadata is screened separately from published file contents."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from check_git_privacy import inspect_commit


class CommitPrivacyTests(unittest.TestCase):
    public = '1+contributor' + '@' + 'users.noreply.github.com'
    private = 'contributor' + '@' + 'example.invalid'

    def commit(self, author=None, committer=None, message='Change the fictional workflow'):
        return ('tree abc\nauthor Contributor <'+(author or self.public)+'> 1 +0000\n'
                'committer Contributor <'+(committer or self.public)+'> 1 +0000\n\n'+message)

    def test_public_identity_passes(self):
        self.assertEqual(inspect_commit('abc',self.commit()),[])

    def test_private_author_or_committer_fails_without_echoing_email(self):
        for field in ['author','committer']:
            result=inspect_commit('abc',self.commit(**{field:self.private}))
            self.assertEqual(result[0]['field'],field)
            self.assertNotIn(self.private,str(result))

    def test_coauthor_and_message_contact_are_screened(self):
        result=inspect_commit('abc',self.commit(message='Co-authored-by: Contributor <'+self.private+'>'))
        self.assertEqual(result[0]['field'],'message_or_trailer')

    def test_lookalike_domain_and_missing_identity_fail(self):
        self.assertTrue(inspect_commit('abc',self.commit(author=self.public+'.invalid')))
        self.assertTrue(inspect_commit('abc','tree abc\n\nNo identity'))


if __name__=='__main__':unittest.main()
