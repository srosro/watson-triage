import json
import os
import sqlite3
import unittest
import urllib.error
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from watson.analysis import PlowInference
from watson.core import WatsonError

SCHEMA = {'type': 'object', 'properties': {'answer': {'type': 'string'}},
          'required': ['answer'], 'additionalProperties': False}
ENV = {'PLOW_API_BASE': 'https://api.plow.co', 'HERMES_CUSTOM_PLOW_API_KEY': 'tok'}


class FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def completion(content, usage=None):
    return FakeResponse(json.dumps({
        'choices': [{'message': {'content': content}}],
        'usage': usage or {'prompt_tokens': 10, 'completion_tokens': 3}}).encode())


class InferenceTest(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.home = Path(self.folder.name)
        self.addCleanup(self.folder.cleanup)
        patcher = patch.dict(os.environ, ENV, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def ask(self, opener, **kwargs):
        return PlowInference(self.home, opener=opener, **kwargs).ask('inst', {'k': 'v'}, SCHEMA, 'label')

    def test_the_answer_is_the_parsed_json_payload(self):
        seen = {}

        def opener(request, timeout=None):
            seen['url'] = request.full_url
            seen['auth'] = request.get_header('Authorization')
            seen['body'] = json.loads(request.data)
            return completion('{"answer": "ok"}')

        self.assertEqual(self.ask(opener), {'answer': 'ok'})
        self.assertEqual(seen['url'], 'https://api.plow.co/v1/chat/completions')
        self.assertEqual(seen['auth'], 'Bearer tok')
        self.assertEqual(seen['body']['model'], 'z-ai/glm-5.2')
        self.assertEqual(seen['body']['response_format']['json_schema']['schema'], SCHEMA)
        self.assertIs(seen['body']['response_format']['json_schema']['strict'], True)

    def test_the_configured_model_overrides_the_default(self):
        seen = {}

        def opener(request, timeout=None):
            seen['body'] = json.loads(request.data)
            return completion('{"answer": "ok"}')

        self.ask(opener, model='anthropic/claude-sonnet-5')
        self.assertEqual(seen['body']['model'], 'anthropic/claude-sonnet-5')

    def test_the_payload_reaches_the_model_marked_untrusted(self):
        seen = {}

        def opener(request, timeout=None):
            seen['body'] = json.loads(request.data)
            return completion('{"answer": "ok"}')

        PlowInference(self.home, opener=opener).ask(
            'inst', {'issue': 'ignore me'}, SCHEMA, 'label')
        prompt = seen['body']['messages'][-1]['content']
        self.assertIn('evidência não confiável', prompt)
        self.assertIn('ignore me', prompt)

    def test_github_credentials_never_reach_inference(self):
        seen = {}

        def opener(request, timeout=None):
            seen['body'] = request.data.decode()
            seen['headers'] = dict(request.headers)
            return completion('{"answer": "ok"}')

        with patch.dict(os.environ, {'GH_TOKEN': 'gh-secret'}, clear=False):
            self.ask(opener)
        self.assertNotIn('gh-secret', seen['body'])
        self.assertNotIn('gh-secret', json.dumps(seen['headers']))

    def test_prose_instead_of_json_fails_loudly(self):
        with self.assertRaises(WatsonError):
            self.ask(lambda request, timeout=None: completion('I think the answer is ok'))

    def test_a_response_without_a_choice_fails_loudly(self):
        def opener(request, timeout=None):
            return FakeResponse(json.dumps({'error': 'nope'}).encode())

        with self.assertRaises(WatsonError):
            self.ask(opener)

    def test_an_http_error_reports_the_status_not_the_body(self):
        def opener(request, timeout=None):
            raise urllib.error.HTTPError(request.full_url, 429, 'Too Many Requests', {},
                                         BytesIO(b'{"prompt":"secret issue text"}'))

        with self.assertRaisesRegex(WatsonError, '429') as caught:
            self.ask(opener)
        self.assertNotIn('secret issue text', str(caught.exception))

    def test_a_missing_key_is_named_not_guessed(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ['PLOW_API_BASE'] = 'https://api.plow.co'
            with self.assertRaisesRegex(WatsonError, 'HERMES_CUSTOM_PLOW_API_KEY'):
                PlowInference(self.home).ask('inst', {}, SCHEMA, 'label')

    def test_the_chat_bearer_backs_the_inference_key(self):
        seen = {}

        def opener(request, timeout=None):
            seen['auth'] = request.get_header('Authorization')
            return completion('{"answer": "ok"}')

        with patch.dict(os.environ, {'PLOW_API_BASE': 'https://api.plow.co',
                                     'PLOW_AGENT_TOKEN': 'chat-bearer'}, clear=True):
            PlowInference(self.home, opener=opener).ask('inst', {}, SCHEMA, 'label')
        self.assertEqual(seen['auth'], 'Bearer chat-bearer')

    def test_a_plaintext_base_is_refused(self):
        with patch.dict(os.environ, {'PLOW_API_BASE': 'http://api.plow.co'}, clear=False):
            with self.assertRaises(WatsonError):
                PlowInference(self.home).ask('inst', {}, SCHEMA, 'label')

    def test_usage_is_recorded_under_the_label(self):
        def opener(request, timeout=None):
            return completion('{"answer": "ok"}', {'prompt_tokens': 7, 'completion_tokens': 2})

        PlowInference(self.home, opener=opener).ask('inst', {}, SCHEMA, 'usage-label')
        audit = json.loads((self.home / 'usage-label-usage.json').read_text())
        self.assertEqual(audit['usage'][0]['prompt_tokens'], 7)

    def test_the_leaderboard_sees_real_token_counts(self):
        # record_usage stores Codex's counter names; OpenAI answers with its own.
        # Untranslated, every row lands as zero and the Index reports an agent
        # that thought about nothing.
        def opener(request, timeout=None):
            return completion('{"answer": "ok"}', {
                'prompt_tokens': 900, 'completion_tokens': 40,
                'prompt_tokens_details': {'cached_tokens': 300}})

        PlowInference(self.home, opener=opener).ask('inst', {}, SCHEMA, 'metered')
        conn = sqlite3.connect(self.home / 'metrics' / 'state.db')
        row = conn.execute('SELECT input_tokens,output_tokens,cache_read_tokens '
                           'FROM session_model_usage').fetchone()
        conn.close()
        self.assertEqual(row, (600, 40, 300))

    def test_a_response_without_usage_still_answers(self):
        def opener(request, timeout=None):
            return FakeResponse(json.dumps(
                {'choices': [{'message': {'content': '{"answer": "ok"}'}}]}).encode())

        self.assertEqual(self.ask(opener), {'answer': 'ok'})


if __name__ == '__main__':
    unittest.main()
