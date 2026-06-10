/**
 * Transactional email via Resend — port of legacy `services/email_service.py`
 * (SMTP/Hostinger -> Resend; same recipients, subjects, display names,
 * template data and plain-text parts. See ../nextjs-migration/email-resend.md).
 *
 * ALL helpers are BEST-EFFORT: every failure is caught and logged
 * (legacy returned `1` on error); they never throw and never fail a request.
 */
import { Resend } from "resend";
import { env } from "@/lib/env";
import {
  otpTemplate,
  invitationTemplate,
  newSignInWarningTemplate,
  changingPasswordTemplate,
} from "./templates";

// Legacy constants (services/email_service.py)
const MAIN_WEBSITE_LINK = "https://sandbox-mei.vercel.app/admin/";
const REGISTER_LINK = "https://sandbox-mei.vercel.app/admin/accept-invite";
const PASSWORD_RESET_AVATAR = "https://banner2.cleanpng.com/20180330/cue/avicnrp87.webp";

/** Lazy Resend client — never constructed at module scope (needs RESEND_API_KEY). */
let _resend: Resend | null = null;
function resendClient(): Resend {
  if (!_resend) _resend = new Resend(env("RESEND_API_KEY"));
  return _resend;
}

/** Build `"Display Name <local@domain>"` from EMAIL_FROM_DOMAIN (default "mie.app"). */
function fromAddress(displayName: string, localPart: string): string {
  const domain = env("EMAIL_FROM_DOMAIN", "mie.app") ?? "mie.app";
  return `${displayName} <${localPart}@${domain}>`;
}

/**
 * Internal send wrapper. Mirrors the legacy pipeline: strips literal `<br>`
 * tags from the HTML (legacy `.replace('<br>','')`) and sends an HTML body
 * with a plain-text alternative. Best-effort — catches everything.
 */
async function sendEmail(args: {
  from: string;
  to: string;
  subject: string;
  html: string;
  text: string;
}): Promise<void> {
  try {
    const html = args.html.replace(/<br>/g, "");
    const { error } = await resendClient().emails.send({
      from: args.from,
      to: args.to,
      subject: args.subject,
      html,
      text: args.text,
    });
    if (error) console.error("email send failed", error);
  } catch (e) {
    console.error("email send failed", e);
  }
}

/** Admin login OTP (legacy `send_email`). */
export async function sendAdminOtp(a: { to: string; otp: string }): Promise<void> {
  try {
    await sendEmail({
      from: fromAddress("MIE OTP", "otp"),
      to: a.to,
      subject: "OTP FOR ADMIN LOGIN",
      html: otpTemplate({ otp_code: a.otp, user_email: a.to }),
      text: `Enter this ${a.otp} to log in`,
    });
  } catch (e) {
    console.error("email send failed", e);
  }
}

/**
 * Admin registration invitation (legacy `send_invitation`).
 * Note: the legacy AllowedAdmin write (when `firstName != "Default"`) belongs
 * to the invite route, not this helper — `inviterEmail` is accepted for seam
 * parity but the email content does not use it (legacy used it only for the
 * AllowedAdmin row).
 */
export async function sendAdminInvitation(a: {
  to: string;
  firstName: string;
  lastName: string;
  inviterEmail: string;
}): Promise<void> {
  try {
    await sendEmail({
      from: fromAddress(`${a.firstName} from Mie`, "invite"),
      to: a.to,
      subject: "Admin Registration Invitation",
      html: invitationTemplate({
        first_name: a.firstName,
        last_name: a.lastName,
        invitee_email_address: a.to,
        main_website_link: MAIN_WEBSITE_LINK,
        register_link: REGISTER_LINK,
      }),
      text: "You have been invited to register as an admin",
    });
  } catch (e) {
    console.error("email send failed", e);
  }
}

/** New-IP/device security alert (legacy `send_warning_about_ip_change`). */
export async function sendNewIpWarning(a: {
  to: string;
  firstName: string;
  lastName: string;
  timeData: string;
  ip: string;
  location: string;
  extraData: string;
}): Promise<void> {
  try {
    await sendEmail({
      from: fromAddress("Mie SECURITY", "security"),
      to: a.to,
      subject: `Security Alert for ${a.to}`,
      html: newSignInWarningTemplate({
        firstName: a.firstName,
        lastName: a.lastName,
        time_data: a.timeData,
        ip_address: a.ip,
        location: a.location,
        extra_data: a.extraData,
      }),
      // legacy plain text part (trailing space included)
      text: `Security Alert for ${a.firstName} ${a.lastName} `,
    });
  } catch (e) {
    console.error("email send failed", e);
  }
}

/** Password reset/change OTP (legacy `send_change_of_password_otp_email`). */
export async function sendPasswordResetOtp(a: { to: string; otp: string }): Promise<void> {
  try {
    await sendEmail({
      from: fromAddress("ADMIN FROM Mie", "noreply"),
      to: a.to,
      subject: "Reset Password?",
      html: changingPasswordTemplate({
        otp_code: a.otp,
        email: a.to,
        avatar: PASSWORD_RESET_AVATAR,
      }),
      text: `Enter this ${a.otp} to log in`,
    });
  } catch (e) {
    console.error("email send failed", e);
  }
}
