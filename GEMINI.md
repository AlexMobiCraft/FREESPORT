# Gemini Added Memories (Специфические правила для Gemini)

- Отвечай и веди документацию исключительно на русском языке
- См. общее руководство: [AGENTS.md](file:///c:/Users/1/DEV/FREESPORT/AGENTS.md)

# Command Validation Rules (Валидация команд)

Это правило специфично для LLM моделей, чтобы избежать ошибок при генерации команд:

- **CRITICAL**: Перед выполнением любой терминальной команды через `run_command`, убедись, что параметр `CommandLine`:
  1. Начинается с валидного имени команды (например, `docker`, `npm`, `python`, `git`), используя только **латинские символы**.
  2. НЕ содержит **кириллических символов** (таких как `с`, `а`, `о`, `е`, которые похожи на латинские `c`, `a`, `o`, `e`).
  3. НЕ имеет ведущих специальных символов или пробелов перед командой.

# Проектные правила и инструкции

Для обеспечения корректной работы в данном проекте, следуй инструкциям в основном руководстве:

- [Работа в Windows и PowerShell](file:///c:/Users/tkachenko/DEV/FREESPORT/AGENTS.md#работа-в-среде-windows-и-terminal)
- [Правила Terminal и SSH (защита от зависаний)](file:///c:/Users/tkachenko/DEV/FREESPORT/AGENTS.md#правила-работы-с-терминалом-и-ssh-защита-от-зависаний)
- [Разработка Frontend (перезапуск Docker)](file:///c:/Users/tkachenko/DEV/FREESPORT/AGENTS.md#правила-разработки-frontend)
- [Разработка и тестирование Backend](file:///c:/Users/tkachenko/DEV/FREESPORT/AGENTS.md#разработка-и-тестирование-backend)
- [Проектная документация (Architecture, Stack)](file:///c:/Users/tkachenko/DEV/FREESPORT/AGENTS.md#справочная-информация)
