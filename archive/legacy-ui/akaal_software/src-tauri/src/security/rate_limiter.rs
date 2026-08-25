use std::collections::HashMap;
use std::sync::{Mutex, OnceLock};

const MAX_FAILED_ATTEMPTS: u32 = 5;
const LOCKOUT_DURATION_SECS: i64 = 900; // 15 minutes

#[derive(Debug, Clone)]
pub struct AttemptRecord {
    pub count: u32,
    pub last_attempt_at: i64,
}

pub struct RateLimiter {
    attempts: Mutex<HashMap<String, AttemptRecord>>,
}

impl RateLimiter {
    pub fn global() -> &'static RateLimiter {
        static INSTANCE: OnceLock<RateLimiter> = OnceLock::new();
        INSTANCE.get_or_init(|| RateLimiter {
            attempts: Mutex::new(HashMap::new()),
        })
    }

    pub fn check_lockout(&self, username: &str) -> Result<(), String> {
        let now = chrono::Utc::now().timestamp();
        let key = username.to_lowercase();

        if let Ok(guard) = self.attempts.lock() {
            if let Some(record) = guard.get(&key) {
                if record.count >= MAX_FAILED_ATTEMPTS {
                    let elapsed = now - record.last_attempt_at;
                    if elapsed < LOCKOUT_DURATION_SECS {
                        let remaining_mins = ((LOCKOUT_DURATION_SECS - elapsed) / 60) + 1;
                        return Err(format!(
                            "Account is temporarily locked due to repeated failed login attempts. Please try again in {} minutes.",
                            remaining_mins
                        ));
                    }
                }
            }
        }
        Ok(())
    }

    pub fn record_failure(&self, username: &str) {
        let now = chrono::Utc::now().timestamp();
        let key = username.to_lowercase();

        if let Ok(mut guard) = self.attempts.lock() {
            let record = guard.entry(key).or_insert(AttemptRecord {
                count: 0,
                last_attempt_at: now,
            });

            // Reset count if previous window has expired
            if now - record.last_attempt_at > LOCKOUT_DURATION_SECS {
                record.count = 1;
            } else {
                record.count += 1;
            }
            record.last_attempt_at = now;
        }
    }

    pub fn reset(&self, username: &str) {
        let key = username.to_lowercase();
        if let Ok(mut guard) = self.attempts.lock() {
            guard.remove(&key);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rate_limiter_lockout() {
        let limiter = RateLimiter::global();
        let test_user = "test_user_lockout";

        limiter.reset(test_user);
        assert!(limiter.check_lockout(test_user).is_ok());

        for _ in 0..4 {
            limiter.record_failure(test_user);
            assert!(limiter.check_lockout(test_user).is_ok());
        }

        // 5th failure triggers lockout
        limiter.record_failure(test_user);
        assert!(limiter.check_lockout(test_user).is_err());

        limiter.reset(test_user);
        assert!(limiter.check_lockout(test_user).is_ok());
    }
}
