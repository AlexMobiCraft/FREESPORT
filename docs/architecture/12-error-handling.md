# 12. Стратегия Обработки Ошибок

### Frontend Error Handling

**React Error Boundaries:**
- Global ErrorBoundary для перехвата React ошибок
- Component-level fallbacks для graceful degradation
- Automatic error reporting to monitoring service

**API Error Handling:**
```typescript
interface ApiError {
  message: string;
  code: string;
  details?: Record<string, any>;
  status: number;
}

// User-friendly error messages
const getErrorMessage = (error: ApiError): string => {
  switch (error.code) {
    case 'NETWORK_ERROR': return 'Проблемы с подключением к интернету';
    case 'VALIDATION_ERROR': return 'Проверьте правильность заполнения полей';
    case 'INSUFFICIENT_STOCK': return 'Товара нет в наличии';
    case 'PAYMENT_FAILED': return 'Ошибка при обработке платежа';
    default: return error.message || 'Произошла неизвестная ошибка';
  }
};
```

**Next.js Error Pages:**
- Custom error.tsx для глобальных ошибок
- not-found.tsx для 404 ошибок
- API route error handling с proper HTTP codes

### Backend Error Handling

**Custom Exception Classes:**
```python
class FreeSportException(Exception):
    default_message = "An error occurred"
    default_code = "FREESPORT_ERROR"
    default_status = status.HTTP_500_INTERNAL_SERVER_ERROR

class ValidationException(FreeSportException):
    default_code = "VALIDATION_ERROR"
    default_status = status.HTTP_400_BAD_REQUEST

class InsufficientStockException(FreeSportException):
    default_code = "INSUFFICIENT_STOCK"
    default_status = status.HTTP_409_CONFLICT

class PaymentException(FreeSportException):
    default_code = "PAYMENT_FAILED"
    default_status = status.HTTP_402_PAYMENT_REQUIRED
```

**Global Exception Handler:**
- Standardized error response format
- Automatic logging for all exceptions
- Different handling for custom vs system exceptions
- Database error fallbacks

**Service Layer Error Handling:**
- Transactional integrity для критических операций
- Graceful fallbacks для external service failures
- Retry logic с exponential backoff

### Circuit Breaker Pattern

**External Service Protection:**
- Circuit breaker для 1C интеграции
- Failure threshold: 5 неудач
- Recovery timeout: 60 секунд
- Fallback to file export при недоступности API

### Error Monitoring

**Error Aggregation:**
- Группировка одинаковых ошибок по hash
- Count tracking для частоты ошибок
- Resolution tracking для bug fixing

**Alert System:**
- Email alerts для critical errors
- Slack integration для development team
- Error rate monitoring и thresholds

**Error Categories:**
- Frontend errors (JavaScript/React)
- Backend errors (Django/API)
- Integration errors (1C/YuKassa)
- Database errors (PostgreSQL)

### Retry Strategies

**Celery Tasks:**
- Max 3 retries с exponential backoff
- Different retry delays по типу ошибки
- Final fallback mechanisms
- Admin notifications при complete failure

**API Calls:**
- Network timeout: 30 секунд
- Retry on 5xx errors (не на 4xx)
- Client-side retry с user feedback

---
