# Notes

Run this before mutating operations if the session may have expired.

If `auth/status` fails or returns no user, run `auth/login` again.

