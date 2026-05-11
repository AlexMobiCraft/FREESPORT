import type { FieldValues, Path, UseFormSetError } from 'react-hook-form';

export type ApiValidationValue =
  | string
  | string[]
  | ApiValidationValue[]
  | { [key: string]: ApiValidationValue }
  | null
  | undefined;

export type ApiErrorData = Record<string, ApiValidationValue> & { detail?: ApiValidationValue };

export type BackendFieldErrorMap<FormInput extends FieldValues> = Partial<
  Record<string, Path<FormInput>>
>;

const MAX_VALIDATION_MESSAGE_DEPTH = 8;
const ARRAY_INDEX_KEY_RE = /^(0|[1-9]\d*)$/;

const isArrayIndexKey = (key: string) => ARRAY_INDEX_KEY_RE.test(key);

export const getValidationEntries = (data: Record<string, ApiValidationValue>) =>
  Object.entries(data).sort(
    ([leftKey], [rightKey]) => Number(isArrayIndexKey(leftKey)) - Number(isArrayIndexKey(rightKey))
  );

export const getValidationMessage = (
  value: ApiValidationValue,
  seenObjects: WeakSet<object> = new WeakSet(),
  depth = 0
): string | undefined => {
  if (depth > MAX_VALIDATION_MESSAGE_DEPTH) {
    return undefined;
  }

  if (typeof value === 'string') {
    return value || undefined;
  }

  if (Array.isArray(value)) {
    if (seenObjects.has(value)) {
      return undefined;
    }
    seenObjects.add(value);

    for (const item of value) {
      const message = getValidationMessage(item, seenObjects, depth + 1);
      if (message) {
        return message;
      }
    }
    return undefined;
  }

  if (value && typeof value === 'object') {
    if (seenObjects.has(value)) {
      return undefined;
    }
    seenObjects.add(value);

    for (const [, item] of getValidationEntries(value as Record<string, ApiValidationValue>)) {
      const message = getValidationMessage(item, seenObjects, depth + 1);
      if (message) {
        return message;
      }
    }
  }

  return undefined;
};

export const getFirstValidationMessage = (data: ApiErrorData): string | undefined => {
  for (const [key, value] of getValidationEntries(data)) {
    if (key === 'detail') {
      continue;
    }

    const message = getValidationMessage(value);
    if (message) {
      return message;
    }
  }

  return getValidationMessage(data.detail);
};

const collectBackendFieldMessages = <FormInput extends FieldValues>(
  value: ApiValidationValue,
  fieldErrorMap: BackendFieldErrorMap<FormInput>,
  messages: Partial<Record<Path<FormInput>, string>>,
  seenObjects: WeakSet<object> = new WeakSet(),
  depth = 0
) => {
  if (!value || typeof value !== 'object' || depth > MAX_VALIDATION_MESSAGE_DEPTH) {
    return;
  }

  if (seenObjects.has(value)) {
    return;
  }
  seenObjects.add(value);

  const entries: Array<readonly [string, ApiValidationValue]> = Array.isArray(value)
    ? value.map((item, index) => [String(index), item] as const)
    : getValidationEntries(value as Record<string, ApiValidationValue>);

  for (const [key, item] of entries) {
    const fieldName = fieldErrorMap[key];
    const message = fieldName ? getValidationMessage(item) : undefined;
    if (fieldName && message && !messages[fieldName]) {
      messages[fieldName] = message;
    }

    collectBackendFieldMessages(item, fieldErrorMap, messages, seenObjects, depth + 1);
  }
};

export const applyBackendFieldErrors = <FormInput extends FieldValues>(
  data: ApiErrorData,
  setError: UseFormSetError<FormInput>,
  fieldErrorMap: BackendFieldErrorMap<FormInput>
): string | undefined => {
  const messages: Partial<Record<Path<FormInput>, string>> = {};
  collectBackendFieldMessages(data, fieldErrorMap, messages);

  for (const [fieldName, message] of Object.entries(messages) as Array<[Path<FormInput>, string]>) {
    setError(fieldName, { type: 'server', message });
  }

  return Object.values(messages).find((message): message is string => typeof message === 'string');
};
