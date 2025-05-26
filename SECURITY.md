# Security Policy

## Supported Versions

The Heijunka project follows [semantic versioning](https://semver.org/) and supports the latest major and minor release.

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

If you discover a security vulnerability, **please do not open a public issue.**  
Instead, email us at [security@yourdomain.com] or contact a maintainer directly via GitHub.  
We will respond promptly and coordinate a fix as soon as possible.

---

## Security Best Practices

The Heijunka project enforces the following security best practices:

- **Strict input validation and sanitization** using Pydantic models with regular expressions and HTML sanitization with `bleach`.
- **CSRF protection** on all state-changing endpoints using `starlette-csrf`.
- **Secure HTTP headers** (CSP, HSTS, X-Frame-Options, etc.) set by the [`secure`](https://github.com/talonsec/secure) middleware.
- **Redis-based distributed rate limiting** enabled on all API endpoints to prevent abuse across multiple instances.
- **JWT authentication** for all users with proper role-based access control.
- **Secure password handling** using bcrypt for constant-time comparison to prevent timing attacks.
- **Comprehensive error handling** with structured error responses and proper logging.
- **Input length validation** to prevent buffer overflow attacks and DoS.
- **No secrets, passwords, or sensitive data** are committed to the repository. All secrets are provided by environment variables.
- **All SQL queries are parameterized** via SQLAlchemy ORM to prevent SQL injection.
- **Regular dependency updates** and vulnerability scanning via [Dependabot](https://github.com/dependabot) or similar.

---

## Key Security Libraries and Configurations

| Area                    | Library           | Usage                                       |
| ----------------------- | ---------------- | ------------------------------------------- |
| Input validation        | Pydantic         | All API payloads use Pydantic models        |
| HTML sanitization       | bleach           | Sanitize HTML content to prevent XSS        |
| CSRF protection         | starlette-csrf   | CSRF middleware for browser-exposed APIs    |
| Security headers        | secure           | Automatic HTTP header hardening             |
| Password hashing        | bcrypt           | Secure password verification with bcrypt    |
| JWT authentication      | python-jose      | Secure token-based authentication           |
| File uploads            | FastAPI, custom  | File validation (type/size) enforced        |
| Rate limiting           | Redis, custom middleware| Distributed rate limiting to prevent abuse |
| Error handling          | FastAPI          | Structured error responses                  |

---

## Guidelines for Contributors

- **Validate all input**: Use Pydantic models for every new endpoint.
- **Never trust user input**: Always sanitize and validate.
- **Never log sensitive data** (e.g., passwords, tokens, PII).
- **Add security tests**: Write tests that attempt XSS, SQLi, and CSRF attacks.
- **Review third-party dependencies**: Prefer well-maintained libraries.
- **Apply the Principle of Least Privilege**: Grant only necessary permissions.
- **Use HTTPS**: Always deploy behind HTTPS in production.
- **Review PRs for security**: All pull requests are reviewed for security impact.

---

## Ongoing Security Maintenance

- **Periodic audits**: Scheduled code and dependency reviews.
- **Automated tools**: Use [Bandit](https://github.com/PyCQA/bandit) and [Safety](https://github.com/pyupio/safety) for scanning.
- **Patch promptly**: Address security advisories within 7 days.

---

## Contact

Questions or concerns? Email [robawtic@gmail.com] or create a private GitHub security advisory.

---

_Last updated: 2024-08-21_
