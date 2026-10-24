"""Synthetic boundary tests; no hidden labels or organizer data."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from code.evidence import Fact, json_facts, parse_file, timestamp
from code.inputs import InputError, load_tables
from code.models import DeletionRequest
from code.pipeline import EvidencePipeline, before_cutoff, classify_request, matches, resolve_identity


def request(text='Delete my account', email='old@example.test'):
    return DeletionRequest('test', email, timestamp('2026-01-01T00:00:00Z'), 'COMPLETE', None, timestamp('2026-02-01T00:00:00Z'), text)


class PipelineTests(unittest.TestCase):
    def test_table_validation(self):
        import csv
        from code.inputs import TABLE_FIELDS
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            for name, fields in TABLE_FIELDS.items():
                with (dataset / (name + '.csv')).open('w', newline='') as handle:
                    csv.writer(handle).writerow(fields)
            self.assertEqual(len(load_tables(dataset)), 5)
            (dataset / 'user_identities.csv').write_text('user_id,email\nuser_1,test@example.test\n')
            with self.assertRaises(InputError):
                load_tables(dataset)

    def test_intent_boundaries(self):
        for text in ('Please remove me from marketing lists only.', 'Correct my surname without removing any records.', "Please don't delete or change anything; send me a copy.", 'This is an information request, not a request to erase it.'):
            self.assertEqual(classify_request(text).decision, 'NOT_APPLICABLE')
        for text in ('Delete my account and the export copy.', 'Je demande la suppression définitive du compte.', 'アカウントの削除を依頼します', '계정의 영구 삭제를 요청합니다', 'Solicito a exclusão permanente da conta.'):
            self.assertEqual(classify_request(text).decision, 'AUTHORIZED')
        self.assertEqual(classify_request('Help me with privacy').decision, 'UNCERTAIN')

    def test_exact_identifier_boundaries(self):
        self.assertFalse(matches('user_100 xold@example.test', {'user_10', 'old@example.test'}))
        self.assertTrue(matches('email="OLD@example.test"', {'old@example.test'}))

    def test_manifest_and_event_cutoffs(self):
        fact = Fact('f', 'line:1', '2026-01-01T00:00:00Z', ('2026-03-01T00:00:00Z',), '', (), 'claim', '')
        self.assertFalse(before_cutoff(fact, request()))
        with self.assertRaises(ValueError):
            timestamp('2026-01-01T00:00:00')

    def test_record_level_json(self):
        source = {'file_id': 'f', 'captured_at': '2026-01-01T00:00:00Z'}
        facts = json_facts({'snapshots': [{'data_store': 'primary', 'records': [{'resource_id': 'account_1', 'email': 'old@example.test'}, {'resource_id': 'account_2', 'email': 'decoy@example.test'}]}]}, source)
        self.assertEqual(len(facts), 2)
        self.assertNotIn('decoy@example.test', facts[0].text)
        self.assertEqual(facts[0].system_id, 'primary')

    def test_historical_identity_excludes_future(self):
        tables = {'user_identities': [{'user_id': 'user_1', 'email': 'future@example.test', 'updated_at': '2026-03-01T00:00:00Z'}], 'user_audit_log': [{'user_id': 'user_1', 'field_name': 'email', 'old_value': 'old@example.test', 'new_value': 'new@example.test', 'audit_id': 'audit_1', 'event_time': '2026-01-01T00:00:00Z'}]}
        links, warnings = resolve_identity(request(), tables)
        self.assertFalse(warnings)
        self.assertIn('user_1', {link.value for link in links})
        self.assertNotIn('future@example.test', {link.value for link in links})

    def test_non_deletion_skips_retrieval(self):
        pipeline = object.__new__(EvidencePipeline)
        with patch('code.pipeline.parse_file', side_effect=AssertionError('retrieved')):
            packet = pipeline.packet(request('Please remove me from marketing lists only.'))
        self.assertEqual(packet.deletion_status, 'NOT_APPLICABLE')
        self.assertEqual(packet.steps_json, [])

    def test_trace_link_and_sql_topology(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            (dataset / 'evidence').mkdir()
            source = {'file_id': 'f', 'captured_at': '2026-01-01T00:00:00Z', 'file_path': 'evidence/test.log'}
            (dataset / source['file_path']).write_text('2026-01-01T00:00:00Z service=search trace_id=t lookup="old@example.test"\n2026-01-01T00:00:01Z service=search trace_id=t resource_id=search_1 result=hit\n')
            facts = parse_file(source, dataset)
            self.assertEqual(len(facts), 1)
            self.assertEqual(facts[0].resource_ids, ('search_1',))
            self.assertEqual(facts[0].kind, 'claim')
            source['file_path'] = 'evidence/test.sql'
            (dataset / source['file_path']).write_text('INSERT INTO "replica" VALUES(\'account_1\',\'account_service\',\'profiles\',\'{"email":"old@example.test"}\',\'2026-01-01T00:00:00Z\');\n')
            fact = parse_file(source, dataset)[0]
            self.assertIn('replica', fact.location)
            self.assertEqual(fact.system_id, 'account_service')

    def test_packet_resource_closure_and_budget(self):
        pipeline = object.__new__(EvidencePipeline)
        pipeline.tables = {'user_identities': [{'user_id': 'user_1', 'name': 'Test Person', 'email': 'old@example.test', 'phone': '', 'email_hash': '', 'updated_at': '2026-01-01T00:00:00Z'}], 'user_audit_log': [], 'deletion_rules': [], 'system_activity': [], 'evidence_files': [{'file_id': 'f', 'captured_at': '2026-01-01T00:00:00Z'}]}
        pipeline.dataset = Path('.')
        pipeline.max_facts = 1
        pipeline.max_chars = 10000
        pipeline.cache = {'f': [Fact('f', '1', '2026-01-01T00:00:00Z', (), '', ('account_1',), 'observation', 'old@example.test account_1'), Fact('f', '2', '2026-01-01T00:00:00Z', (), '', ('account_1',), 'observation', 'account_1 replica')]}
        packet = pipeline.packet(request())
        self.assertEqual(len(packet.facts), 1)
        self.assertEqual(packet.omitted_facts, 1)
        self.assertIn('packet_truncated_requires_followup', packet.uncertainty)


if __name__ == '__main__':
    unittest.main()
