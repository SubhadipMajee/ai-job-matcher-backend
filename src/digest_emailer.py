"""
digest_emailer.py — sends the daily job digest using the Resend API.

send_digest_email(to_email, jobs)
  • Expects jobs already filtered (new only) and sorted by score desc.
  • Caps at top 10 jobs per email.
  • Does nothing if the jobs list is empty (no empty emails sent).
  • Reads RESEND_API_KEY and FROM_EMAIL from environment variables.
"""

import os
import resend
from dotenv import load_dotenv

load_dotenv()


def _build_html(jobs: list[dict]) -> str:
    """Render a clean HTML email body for the top job matches."""

    rows = ""
    for job in jobs[:10]:
        title    = job.get("title",    "N/A")
        company  = job.get("company",  "N/A")
        location = job.get("location", "N/A")
        score    = job.get("score",    0)
        link     = job.get("link",     "#")

        # Colour the score badge green / amber / red
        if score >= 60:
            badge_color = "#16a34a"   # green
        elif score >= 30:
            badge_color = "#ca8a04"   # amber
        else:
            badge_color = "#dc2626"   # red

        rows += f"""
        <tr>
          <td style="padding:12px 8px;border-bottom:1px solid #e5e7eb;">
            <strong style="font-size:15px;">{title}</strong><br>
            <span style="color:#6b7280;font-size:13px;">{company} &bull; {location}</span>
          </td>
          <td style="padding:12px 8px;border-bottom:1px solid #e5e7eb;text-align:center;">
            <span style="background:{badge_color};color:#fff;padding:4px 10px;
                         border-radius:9999px;font-size:13px;font-weight:700;">
              {score}%
            </span>
          </td>
          <td style="padding:12px 8px;border-bottom:1px solid #e5e7eb;text-align:center;">
            <a href="{link}"
               style="background:#2563eb;color:#fff;padding:6px 14px;border-radius:6px;
                      text-decoration:none;font-size:13px;font-weight:600;">
              Apply
            </a>
          </td>
        </tr>"""

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:sans-serif;">
  <div style="max-width:640px;margin:32px auto;background:#fff;
              border-radius:12px;overflow:hidden;border:1px solid #e5e7eb;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);
                padding:28px 32px;color:#fff;">
      <h1 style="margin:0;font-size:22px;font-weight:800;">
        🎯 Your Daily Job Digest
      </h1>
      <p style="margin:6px 0 0;opacity:.85;font-size:14px;">
        {len(jobs[:10])} new match{"es" if len(jobs[:10]) != 1 else ""} based on your skills
      </p>
    </div>

    <!-- Table -->
    <div style="padding:24px 32px;">
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr style="background:#f3f4f6;">
            <th style="padding:10px 8px;text-align:left;font-size:12px;
                       color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">
              Job
            </th>
            <th style="padding:10px 8px;text-align:center;font-size:12px;
                       color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">
              Match
            </th>
            <th style="padding:10px 8px;text-align:center;font-size:12px;
                       color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">
              Link
            </th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>

    <!-- Footer -->
    <div style="padding:20px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;
                font-size:12px;color:#9ca3af;text-align:center;">
      You're receiving this because you set up a daily digest.
      Scores are based on keyword match between your saved skills and the job description.
    </div>
  </div>
</body>
</html>"""


def send_digest_email(to_email: str, jobs: list[dict]) -> bool:
    """
    Send the digest email to `to_email`.

    Parameters
    ----------
    to_email : recipient address
    jobs     : new, pre-filtered, pre-sorted list of matched jobs

    Returns True if an email was sent, False if skipped (empty jobs list).
    """
    if not jobs:
        return False   # nothing new — don't send an empty email

    resend.api_key = os.getenv("RESEND_API_KEY")
    from_email     = os.getenv("FROM_EMAIL", "digest@resend.dev")

    resend.Emails.send({
        "from":    from_email,
        "to":      [to_email],
        "subject": f"🎯 {len(jobs[:10])} new job match{'es' if len(jobs[:10]) != 1 else ''} for you today",
        "html":    _build_html(jobs),
    })

    return True
