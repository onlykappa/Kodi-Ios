"""ISSUE-350: the IPA build job (import-review.yml, job `review`) was killed by its own 10-minute limit while publishing the release
(run 43769622376: the IPA was built and validated, step 12 "Publish raw IPA" was cancelled at 10 min 12 s). Every added test suite makes the
job longer, so the limit must leave room."""
import re
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/import-review.yml'


class Limits(unittest.TestCase):
    def test_the_ipa_build_job_has_room_to_publish(self):
        text = WORKFLOW.read_text()
        job = text[text.index('\n  review:'):]
        limit = int(re.search(r'timeout-minutes:\s*(\d+)', job).group(1))
        self.assertGreaterEqual(limit, 20, 'the job ran 10 min 12 s before publishing; keep at least 20 minutes')
        self.assertLessEqual(limit, 60)

    def test_it_still_publishes_the_ipa(self):
        self.assertIn('Publish raw IPA as a prerelease download', WORKFLOW.read_text())


if __name__ == '__main__':
    unittest.main()
