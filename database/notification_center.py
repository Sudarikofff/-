"""Common notification feed. New sources implement the same provider interface."""
from database.osago_notifications import OsagoNotifications


class OsagoNotificationProvider:
    key = 'osago'
    label = 'ОСАГО'

    def __init__(self, repository=None):
        self.repository = repository or OsagoNotifications()

    def refresh(self, today=None):
        state = self.repository.refresh(today)
        rows = []
        for record in state['rows']:
            rows.append(dict(
                id=record['id'], category=self.label, title=record['title'],
                full_name=record['full_name'], subject=record['vehicle'],
                due_date=record['expiry_date'], days=record['days'], status=record['status'],
                reading=record['reading'], is_read=record['is_read'], deferred=record['deferred'],
                snoozed_until=record['snoozed_until'], personnel_id=record['personnel_id'],
                section='Личный транспорт', search_text=record['insurance_number'] or '',
            ))
        warnings = []
        if state['invalid_dates']:
            warnings.append(f"ОСАГО: проверьте некорректные даты ({state['invalid_dates']}) в разделе «Контроль сроков».")
        return dict(rows=rows, enabled=state['settings']['enabled'],
                    startup_summary=state['settings']['startup_summary'], warnings=warnings)

    def mark_read(self, ident): self.repository.mark_read(ident)
    def mark_all_read(self, today=None): self.repository.mark_all_read(today)
    def snooze(self, ident, until, today=None): self.repository.snooze(ident, until, today)
    def resume(self, ident): self.repository.resume(ident)


class NotificationCenter:
    """Providers return generic rows; read/snooze actions route by a scoped ID."""
    def __init__(self, providers=None):
        providers = [OsagoNotificationProvider()] if providers is None else providers
        self.providers = {}
        for provider in providers:
            if not provider.key or ':' in provider.key or provider.key in self.providers:
                raise ValueError('У каждого источника уведомлений должен быть уникальный ключ без двоеточия.')
            self.providers[provider.key] = provider

    def refresh(self, today=None):
        rows, warnings, sources = [], [], []
        for key, provider in self.providers.items():
            state = provider.refresh(today)
            sources.append(dict(key=key, label=provider.label, enabled=state['enabled']))
            warnings.extend(state.get('warnings', []))
            if not state['enabled']:
                continue
            for row in state['rows']:
                rows.append(dict(row, id=f"{key}:{row['id']}",
                                 source=key, startup_summary=state['startup_summary']))
        rows.sort(key=lambda row: (row['due_date'] or '9999', row['full_name'], row['id']))
        return dict(rows=rows, sources=sources, warnings=warnings,
                    settings=dict(enabled=any(source['enabled'] for source in sources),
                                  startup_summary=any(row['startup_summary'] for row in rows)))

    def _target(self, notification_id):
        source, separator, ident = str(notification_id).partition(':')
        if not separator or source not in self.providers or not ident.isdigit():
            raise ValueError('Неизвестное уведомление. Обновите список.')
        return self.providers[source], int(ident)

    def mark_read(self, notification_id):
        provider, ident = self._target(notification_id)
        provider.mark_read(ident)

    def mark_all_read(self, today=None):
        for provider in self.providers.values():
            provider.mark_all_read(today)

    def snooze(self, notification_id, until, today=None):
        provider, ident = self._target(notification_id)
        provider.snooze(ident, until, today)

    def resume(self, notification_id):
        provider, ident = self._target(notification_id)
        provider.resume(ident)
