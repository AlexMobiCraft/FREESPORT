/**
 * Версии формулировок согласия, которые показывают формы (стори 41.9).
 *
 * Значения обязаны совпадать с действующими ревизиями реестра
 * `backend/apps/common/consent_texts.json`; расхождение ловит страж
 * `src/__tests__/consent-texts-registry.test.tsx`, который читает тот же файл.
 *
 * Почему версия зашита в бандл, а не запрашивается у сервера. Она должна
 * доказывать, какой текст был на экране, а не какой действует на сервере сейчас.
 * Константа собирается в тот же бандл, что и сам текст чекбокса, поэтому вкладка,
 * открытая до правки формулировки, отправит прежнюю версию — и сервер отклонит
 * запрос с требованием обновить страницу. Значение, полученное запросом в момент
 * отправки, было бы всегда актуальным и ничего не доказывало бы.
 */
export const CONSENT_TEXT_VERSIONS = {
  /** Единственный чекбокс форм подписки (SubscribeForm, ElectricSubscribeForm). */
  newsletter: '2026-08-30-77dbceaf',
  /** Обязательный чекбокс ПДн форм регистрации (RegisterForm, B2BRegisterForm). */
  registrationPdp: '2026-09-09-de992f50',
  /** Необязательный маркетинговый чекбокс форм регистрации. */
  registrationMarketing: '2026-09-09-e26471e4',
} as const;

/**
 * Машинный код отказа, когда показанная формулировка устарела или версия не
 * пришла. Сервер отдаёт его верхним уровнем ответа `400`:
 * `{ error: 'consent_text_outdated', details: { <поле>: [сообщение] } }`.
 *
 * Код нужен именно на верхнем уровне: DRF-код ошибки (`ErrorDetail.code`) в JSON
 * не попадает, а у пропущенного поля он и вовсе `required`. Узнавать этот случай
 * по тексту сообщения нельзя — формулировку ошибки правят.
 */
export const CONSENT_TEXT_OUTDATED_CODE = 'consent_text_outdated';

/** Запасной текст: показывается, если сервер не прислал сообщение в `details`. */
export const CONSENT_TEXT_OUTDATED_MESSAGE =
  'Текст согласия обновился. Обновите страницу и подтвердите согласие заново.';

/** Поля, которыми формы доказывают показанную формулировку. */
const CONSENT_TEXT_VERSION_FIELDS = [
  'consent_text_version',
  'pdp_consent_text_version',
  'marketing_consent_text_version',
];

type ConsentTextOutdatedBody = {
  error?: unknown;
  details?: Record<string, unknown>;
};

/** Ответ сервера — отказ по устаревшей версии формулировки? */
export const isConsentTextOutdated = (data: unknown): boolean =>
  !!data &&
  typeof data === 'object' &&
  (data as ConsentTextOutdatedBody).error === CONSENT_TEXT_OUTDATED_CODE;

/**
 * Сообщение для человека из ответа `consent_text_outdated`.
 * `null` — ответ не про версию формулировки, обрабатывать как обычную валидацию.
 */
export const getConsentTextOutdatedMessage = (data: unknown): string | null => {
  if (!isConsentTextOutdated(data)) {
    return null;
  }

  const details = (data as ConsentTextOutdatedBody).details;
  if (details && typeof details === 'object') {
    // Сначала поля версии: в `details` могут лежать и попутные ошибки запроса.
    const ordered = [
      ...CONSENT_TEXT_VERSION_FIELDS.filter(field => field in details),
      ...Object.keys(details).filter(field => !CONSENT_TEXT_VERSION_FIELDS.includes(field)),
    ];
    for (const field of ordered) {
      const messages = details[field];
      if (Array.isArray(messages) && typeof messages[0] === 'string' && messages[0]) {
        return messages[0];
      }
    }
  }

  return CONSENT_TEXT_OUTDATED_MESSAGE;
};
