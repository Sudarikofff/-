import unittest
from database.notification_center import NotificationCenter


class ExampleProvider:
    def __init__(self, key, label, enabled=True, startup=True, due_date='2026-12-01'):
        self.key, self.label = key, label
        self.enabled, self.startup, self.due_date = enabled, startup, due_date
        self.actions = []

    def refresh(self, today=None):
        return dict(enabled=self.enabled, startup_summary=self.startup, warnings=[], rows=[dict(
            id=1, category=self.label, full_name='Тест', title='Напоминание', subject='Документ',
            due_date=self.due_date, is_read=False, deferred=False, days=7, section='Военная служба',
            personnel_id=10, reading='Новое', status='Предстоит', snoozed_until=None,
        )])

    def mark_read(self, ident): self.actions.append(('read', ident))
    def mark_all_read(self, today=None): self.actions.append(('all', today))
    def snooze(self, ident, until, today=None): self.actions.append(('snooze', ident, until))
    def resume(self, ident): self.actions.append(('resume', ident))


class NotificationCenterTests(unittest.TestCase):
    def test_combines_sources_with_colliding_local_ids_and_sorts_dates(self):
        first = ExampleProvider('first', 'Первый', due_date='2026-12-01')
        second = ExampleProvider('second', 'Второй', due_date='2026-11-01')
        rows = NotificationCenter([first, second]).refresh()['rows']
        self.assertEqual([r['id'] for r in rows], ['second:1', 'first:1'])
        self.assertEqual([r['category'] for r in rows], ['Второй', 'Первый'])

    def test_actions_route_only_to_the_correct_source(self):
        first, second = ExampleProvider('first', 'Первый'), ExampleProvider('second', 'Второй')
        center = NotificationCenter([first, second])
        center.mark_read('first:1')
        center.snooze('second:1', '2026-12-01')
        center.resume('second:1')
        self.assertEqual(first.actions, [('read', 1)])
        self.assertEqual(second.actions, [('snooze', 1, '2026-12-01'), ('resume', 1)])
        center.mark_all_read()
        self.assertEqual(first.actions[-1], ('all', None))
        self.assertEqual(second.actions[-1], ('all', None))

    def test_disabled_source_cannot_add_rows_and_startup_is_per_source(self):
        first = ExampleProvider('first', 'Первый', enabled=False)
        second = ExampleProvider('second', 'Второй', startup=False)
        state = NotificationCenter([first, second]).refresh()
        self.assertEqual(len(state['rows']), 1)
        self.assertTrue(state['settings']['enabled'])
        self.assertFalse(state['settings']['startup_summary'])
        self.assertFalse(state['rows'][0]['startup_summary'])
        self.assertEqual(len(state['sources']), 2)

    def test_invalid_ids_and_duplicate_source_keys_are_rejected(self):
        provider = ExampleProvider('first', 'Первый')
        center = NotificationCenter([provider])
        for ident in ('1', 'other:1', 'first:bad'):
            with self.assertRaises(ValueError): center.mark_read(ident)
        with self.assertRaises(ValueError): NotificationCenter([provider, provider])


if __name__ == '__main__':
    unittest.main()
