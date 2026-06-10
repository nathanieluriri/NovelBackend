/**
 * HTML email templates — direct ports of the legacy `string.Template` files in
 * `../app/email_templates/*.py` (otp_template, invitation_template,
 * new_sign_in_warning, changing_password_template).
 *
 * Structure/content kept verbatim (including the odd quoted-printable
 * artifacts in the OTP template). The only intentional change: the password
 * template's unclosed-`</html>` bug is fixed (cosmetic, per email-resend.md).
 *
 * SECURITY: every interpolated variable is HTML-escaped via `esc()` before it
 * reaches the markup (the legacy Python string.Template did not escape, allowing
 * HTML injection via user-controlled names/emails/geo data). Escaping is a no-op
 * for ordinary values, so the rendered email is unchanged for legitimate data.
 * URL-valued fields (avatar src) additionally go through `safeUrl()`, which only
 * admits http/https and drops anything else.
 */

/** HTML-escape a value for safe interpolation into text or quoted attributes. */
function esc(value: unknown): string {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Escaped http/https URL, or "" for any non-http(s) / unparseable value. */
function safeUrl(value: unknown): string {
  const raw = String(value ?? "").trim();
  try {
    const u = new URL(raw);
    if (u.protocol === "http:" || u.protocol === "https:") return esc(u.toString());
  } catch {
    /* not a valid URL */
  }
  return "";
}

/** `otp_template.py` — vars `$otp_code`, `$user_email`. */
export function otpTemplate(vars: { otp_code: string; user_email: string }): string {
  return `
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="UTF-8"/>
    <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
    <meta name="viewport" content="width=device-width, initial-scale=
=1.0"/>

    <title>Mie</title>
</head>

<head>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        *:focus {
            outline: none;
        }

        html {
            font: 62.5% / 1.15 sans-serif; /* 1rem */
            max-width: 100%;
        }

        body {
            margin: 0;
            font-family: sans-serif;
            background: #f7f8fa;
        }

        table {
            border-spacing: 0;
            box-sizing: border-box;
            margin: 0;
            width: 100%;
        }

        td {
            padding: 0;
        }

        .wrapper {
            margin: 0 auto;
            table-layout: fixed;
            width: 100%;
            max-width: 1000px;
            padding: 14px;
            background: #f7f8fa;
            border: 1px solid #f7f8fa;
        }

        .main {
            width: 100%;
            /*max-width: 720px;*/
            background-color: #ffffff;
            font-family: 'DM Sans', sans-serif;
            box-shadow: 0px 4px 36px 1px rgba(0, 0, 0, 0.06);
            overflow: hidden;
        }

        .Mie-email-template--header {
            padding: 48px 0 20px;
            text-align: center;
            border-bottom: 2px solid #f7f5f5;
        }

        .Mie-email-template--header > img {
            width: 200px;
        }

        .Mie-email-template--body-wrapper {
            margin: 28px auto;
            padding: 24px 36px 0;
            width: 100%;
            max-width: 772px;
            font-family: 'DM Sans', sans-serif;
            font-style: normal;
            font-weight: 400;
            font-size: 18px;
            line-height: 226%;
            letter-spacing: -0.003em;
            color: #393939 !important;
        }

        .Mie-email-template--body-wrapper > h4 {
            text-align: left;
            margin-bottom: 0;
        }

        .Mie-email-template--body-wrapper > p {
            text-align: justify;
            width: 100%;
            max-width: 630px;
        }

        .Mie-email-template--body-wrapper > p > a {
            color: #365899;
        }

        .thank-you-text {
            margin: 50px 0 16px;
        }

        .Mie-email-template--otp-code {
            width: 100%;
            max-width: 772px;
            margin: 20px auto 32px;
            padding: 14px 0;
            border-style: solid;
            border-width: 1px;
            border-left: 0;
            border-right: 0;
            border-image: linear-gradient(45deg, #405896, #4a8eb9) 1;
        }

        .Mie-email-template--otp-code > p {
            font-family: 'Mori Gothic', sans-serif;
            font-style: normal;
            font-weight: 400;
            font-size: 48px;
            line-height: 200%;
            letter-spacing: -0.003em;
            color: #365899;
            text-align: center;
        }

        .Mie-email-template--app-and-sales {
            margin: 16px auto 48px;
            padding: 0 36px;
            width: 100%;
            max-width: 772px;
            font-family: 'Mori Gothic', sans-serif;
            font-style: normal;
            font-weight: 400;
            font-size: 16px;
            line-height: 26px;
            letter-spacing: -0.003em;
            color: #393939;
        }

        .app-stores {
            margin: 20px 0;
        }

        .app-stores > a:not(:last-child) {
            margin-right: 24px;
        }

        .app-stores > a > img {
            width: 194px;
        }

        .Mie-email-template--app-and-sales > span {
            margin: 16px 0 0;
        }

        .Mie-email-template--app-and-sales > div {
            margin: 8px 0;
        }

        .Mie-email-template--app-and-sales > a,
        .Mie-email-template--app-and-sales > div > a {
            color: #393939;
        }


        .Mie-email-template--footer {
            width: 100%;
            padding: 0 0 36px;
            text-align: center;
            background: #f7f8fa;
        }

        .footer-border-gradient {
            margin-bottom: 256px;
            display: block;
            width: 100%;
            height: 5px;
            background: #405896;
            background: linear-gradient(45deg, #405896, #4a8eb9);
        }

        .Mie-email-template--footer > img {
            width: 78px;
        }

        .Mie-email-template--footer > p {
            font-family: 'Mori Gothic', sans-serif;
            font-style: normal;
            font-weight: 400;
            font-size: 18px;
            line-height: 29px;
            letter-spacing: -0.003em;
            color: #000000;
            margin: 16px 0;
            text-align: center;
        }

        .footer-text {
            width: 100%;
            padding: 0 22px;
            max-width: 772px;
            font-family: 'Mori Gothic', sans-serif;
            font-style: normal;
            font-weight: 300;
            font-size: 16px;
            line-height: 176%;
            text-align: center;
            letter-spacing: -0.003em;
            margin: 0 auto;
            color: #757474;
        }

        .footer-text > span.unsubscribe {
            font-weight: 400;
        }

        .footer-text > span.user-email {
            text-decoration: underline;
        }

        .footer-text > span > a {
            color: #757474;
        }

        @media screen and (max-width: 432px) {
            .main {
                border-radius: 16px;
                font-size: 14px;
            }

            .Mie-email-template--header {
                margin: 0 12px;
                padding: 16px 0;
                border-bottom: 1px solid #f7f5f5;
            }

            .Mie-email-template--header > img {
                width: 100px;
            }

            .Mie-email-template--body-wrapper {
                margin: 20px 0 0;
                font-size: 14px;
                padding: 30px 12px 0;
            }

            .Mie-email-template--body-wrapper > .thank-you-text {
                margin: 30px 0 16px;
            }

            .Mie-email-template--app-and-sales {
                margin: 20px 0;
                font-size: 14px;
                padding: 0 12px;
            }

            .app-stores {
                margin: 20px 0;
            }

            .app-stores > a:not(:last-child) {
                margin-right: 12px;
            }

            .app-stores > a > img {
                width: 120px;
            }

            .Mie-email-template--footer {
                border: none;
            }

            .Mie-email-template--footer > img {
                width: 45px;
            }

            .Mie-email-template--footer > p {
                font-size: 16px;
            }

            .footer-text {
                font-size: 14px;
            }
        }
    </style>
</head>
<body>
<div class="wrapper">
    <table class="main" width="100%">
        <tr>
            <td>
                <table>
                    <tr>
                        <td class="Mie-email-template--header">
                        </td>
                    </tr>
                </table>
                <table>
                    <tr>
                        <td>
                            <div style="align-items: center; justify-self: center;" class="Mie-email-template--body-wrapp=
er">
                                <h4>Hello <strong>there</strong>, </h4>
                                <p>
                                   Copy the One Time Password (OTP) below and paste it in the app to verify you are the user logging in.
                                </p>
                            </div>
                        </td>
                    </tr>
                </table>

                <table>
                    <tr>
                        <td>
                            <div class="Mie-email-template--otp-code">
                                <p>${esc(vars.otp_code)}</p>
                            </div>
                        </td>
                    </tr>
                </table>

                <table >
                    <tr>
                        <td>
                            <div style="justify-self: center;" class="Mie-email-template--body-wrapp=
er">
                                <p>
                                    DO NOT SHARE OR SEND THIS CODE TO ANYONE!
                                </p>
                            </div>
                        </td>
                    </tr>
                </table>

                <table style="height: 300px;">
                    <tr>
                        <td>
                            <div class="Mie-email-template--footer">
                                <div class="footer-border-gradient"></div=
>
                                <img  style="width: 50px; height: 50px; border-radius: 25%; margin-top:10px ;"  src="https://iili.io/3DKqndN.jpg" alt=
="Mie Logo"/>
                                <p style="padding: 0 22px">Mie. All rights reserved.</p>
                                <div class="footer-text">
                                    This email was intended for <span class=
="user-email">${esc(vars.user_email)}</span>. This message
                                    is intended only for the personal and confidential use of the designated recipient(s). If you
                                    are not the intended recipient of this message you are hereby notified that any review,
                                    dissemination, distribution or copying of this message is strictly prohibited.

                                </div>
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</div>
</body>
</html>

`;
}

/** `invitation_template.py` — vars `$first_name $last_name $invitee_email_address $main_website_link $register_link`. */
export function invitationTemplate(vars: {
  first_name: string;
  last_name: string;
  invitee_email_address: string;
  main_website_link: string;
  register_link: string;
}): string {
  return `
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=US-ASCII">
    <title>${esc(vars.first_name)} ${esc(vars.last_name)} invited you to collaborate on the Mie Project </title>
  </head>
<body bgcolor="#fafafa" topmargin="0" leftmargin="0" marginheight="0" marginwidth="0" style="width: 100% !important; min-width: 100%; -webkit-font-smoothing: antialiased; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; background-color: #fafafa; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; text-align: center; line-height: 20px; font-size: 14px; margin: 0; padding: 0;">
  <table class="body" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: center; height: 100%; width: 100%; background-color: #fafafa; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0;" bgcolor="#fafafa">
    <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
      <td class="center" align="center" valign="top" style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0;">
        <center style="width: 100%; min-width: 580px;">
        <table class="row header" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: center; width: 100%; position: relative; padding: 0px;">
            <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
              <td class="center" align="center" style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0;" valign="top">
                <center style="width: 100%; min-width: 580px;">
                  <table class="container" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: inherit; width: 580px; margin: 0 auto; padding: 0;">
                    <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
                      <td class="wrapper last" style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; position: relative; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0 0px 0 0;" align="center" valign="top">
                        <table class="twelve columns" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: center; width: 540px; margin: 0 auto; padding: 0;">
                          <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
                            <td style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0px 0px 10px;" align="center" valign="top">
                            </td>
                            <td class="expander" style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; visibility: hidden; width: 0px; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0;" align="center" valign="top"></td>
                          </tr>
                        </table>
</td>
                    </tr>
                  </table>
</center>
              </td>
            </tr>
          </table>
<table class="container" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: inherit; width: 580px; margin: 0 auto; padding: 0;">
            <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
              <td style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0;" align="center" valign="top">
                <table class="row" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: center; width: 100%; position: relative; display: block; padding: 0px;">
                  <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
                    <td class="wrapper last" style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; position: relative; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0 0px 0 0;" align="center" valign="top">
                      <div class="panel" style="background: #ffffff; background-color: #ffffff; border-radius: 3px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); padding: 20px; border: 1px solid #dddddd;">
                        <table class="twelve columns" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: center; width: 540px; margin: 0 auto; padding: 0;">
                          <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
                            <td style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0px 0px 0;" align="center" valign="top">
                              <div class="email-content">
                                <h1 class="primary-heading" style="color: #333; font-family: 'Helvetica Neue',Helvetica,Arial,sans-serif; font-weight: 300; text-align: center; line-height: 1.2; word-break: normal; font-size: 24px; margin: 10px 0 25px; padding: 0;" align="center">${esc(vars.first_name)} ${esc(vars.last_name)} Invited you to Use<br><strong> Mie </strong> Story App As an Admin</h1>
                                <hr class="rule" style="color: #d9d9d9; background-color: #d9d9d9; height: 1px; margin: 20px 0; border-style: none;">
                                <p style="word-wrap: normal; hyphens: none; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 14px; font-weight: normal; color: #333; line-height: 20px; text-align: left; margin: 15px 0 5px; padding: 0;" align="left">
                                  You can <a href="${esc(vars.register_link)}" style="color: #4183C4; text-decoration: none;">accept or Ignore</a> this invitation.
                                    You can also visit <a href="${esc(vars.main_website_link)}" style="color: #4183C4; text-decoration: none;">Mie Story App</a> to learn a bit more about them.
                                </p>
                                <p style="word-wrap: normal; hyphens: none; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 14px; font-weight: normal; color: #333; line-height: 20px; text-align: left; margin: 15px 0 5px; padding: 0;" align="left">
                                  This invitation will expire in 7 days.
                                </p>
                                <div class="cta-button-wrap cta-button-wrap-centered" style="text-align: center; color: #ffffff; padding: 20px 0 25px;" align="center">
                                  <a class="cta-button" href="${esc(vars.register_link)}" style="display: inline-block; color: #fff; font-size: 14px; font-weight: 600; background-color: #4183C4; text-decoration: none; width: auto !important; text-align: center; border-radius: 5px; -webkit-border-radius: 5px; box-shadow: 0px 3px 0px #25588c; letter-spacing: normal; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; -webkit-text-size-adjust: none; margin: 0 auto; padding: 6px 12px;">View invitation</a>
                                </div>
                                <p class="email-body-subtext" style="word-wrap: normal; hyphens: none; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 13px; font-weight: normal; color: #333; line-height: 20px; text-align: left; margin: 15px 0 5px; padding: 0;" align="left">
                                  <strong>Note:</strong> This invitation was intended for <strong>${esc(vars.invitee_email_address)}</strong>.
                                </p>
                                <hr class="rule" style="color: #d9d9d9; background-color: #d9d9d9; height: 1px; margin: 20px 0; border-style: none;">
                                <p class="email-text-small email-text-gray" style="word-wrap: normal; hyphens: none; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 12px; font-weight: normal; color: #777777; line-height: 20px; text-align: left; margin: 15px 0 5px; padding: 0;" align="left">
                                  <strong>Button not working?</strong> Copy and paste this link into your browser:
                                  <br><a href="${esc(vars.register_link)}" style="color: #4183C4; text-decoration: none;">${esc(vars.register_link)}</a>
                                </p>
                              </div>
</td>
                            <td class="expander" style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; visibility: hidden; width: 0px; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0;" align="center" valign="top"></td>
                          </tr>
                        </table>
</div>
</td>
                  </tr>
                </table>
</td>
            </tr>
          </table>
<table class="row layout-footer" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: center; width: 100%; position: relative; padding: 0px;">
            <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
              <td class="center" align="center" style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0;" valign="top">
                <center style="width: 100%; min-width: 580px;">
                  <table class="container" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: inherit; width: 580px; margin: 0 auto; padding: 0;">
                    <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
                      <td class="wrapper last" style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; position: relative; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0 0px 0 0;" align="center" valign="top">
                        <table class="twelve columns" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: center; width: 540px; margin: 0 auto; padding: 0;">
                          <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
                            <td style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0px 0px 10px;" align="center" valign="top">
                            </td>
                          </tr>
                        </table>
</td>
                    </tr>
                  </table>
</center>
              </td>
            </tr>
          </table>
</center>
      </td>
    </tr>
  </table>
</body>
</html>
`;
}

/** `new_sign_in_warning.py` — vars `$firstName $lastName $time_data $ip_address $location $extra_data`. */
export function newSignInWarningTemplate(vars: {
  firstName: string;
  lastName: string;
  time_data: string;
  ip_address: string;
  location: string;
  extra_data: string;
}): string {
  return `
<!DOCTYPE html>
<html lang="en">
  <head>
    <title>A New Admin Login </title>
    <!--[if !mso]><!-- -->
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <!--<![endif]-->
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style type="text/css">
      #outlook a { padding: 0; }
      .ReadMsgBody { width: 100%; }
      .ExternalClass { width: 100%; }
      .ExternalClass * { line-height: 100%; }
      body {
        margin: 0;
        padding: 0;
        -webkit-text-size-adjust: 100%;
        -ms-text-size-adjust: 100%;
      }
      table, td {
        border-collapse: collapse;
        mso-table-lspace: 0pt;
        mso-table-rspace: 0pt;
      }
      img {
        border: 0;
        height: auto;
        line-height: 100%;
        outline: none;
        text-decoration: none;
        -ms-interpolation-mode: bicubic;
      }
      p { display: block; margin: 13px 0; }
    </style>

    <!--[if !mso]><!-->
    <style type="text/css">
      @media only screen and (max-width: 480px) {
        @-ms-viewport { width: 320px; }
        @viewport { width: 320px; }
      }
    </style>
    <!--<![endif]-->

    <!--[if mso]>
    <xml>
      <o:OfficeDocumentSettings>
        <o:AllowPNG />
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
    <![endif]-->

    <!--[if lte mso 11]>
    <style type="text/css">
      .outlook-group-fix {
        width: 100% !important;
      }
    </style>
    <![endif]-->

    <style type="text/css">
      @media only screen and (min-width: 480px) {
        .mj-column-per-100 {
          width: 100% !important;
          max-width: 100%;
        }
      }
      @media only screen and (max-width: 480px) {
        table.full-width-mobile { width: 100% !important; }
        td.full-width-mobile { width: auto !important; }
      }

      h1 {
        font-family: -apple-system, system-ui, BlinkMacSystemFont;
        font-size: 24px;
        font-weight: 600;
        line-height: 24px;
        text-align: left;
        color: #333333;
        padding-bottom: 18px;
      }
      p {
        font-family: -apple-system, system-ui, BlinkMacSystemFont;
        font-size: 15px;
        font-weight: 300;
        line-height: 24px;
        text-align: left;
        color: #333333;
      }
      a {
        color: #0867ec;
        font-weight: 400;
      }
      a.footer-link {
        color: #888888;
      }
      strong {
        font-weight: 500;
      }
    </style>
  </head>

  <body style="background-color: #ffffff">
    <div style="display: none; font-size: 1px; color: #ffffff; line-height: 1px; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;">
      Your Mie account has been accessed from a new IP address
    </div>

    <div style="background-color: #ffffff">
      <!--[if mso | IE]>
      <table align="center" border="0" cellpadding="0" cellspacing="0" style="width:600px;" width="600">
        <tr><td style="line-height:0px;font-size:0px;mso-line-height-rule:exactly;">
      <![endif]-->

      <div style="background: #ffffff; background-color: #ffffff; margin: 0px auto; max-width: 600px;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="background: #ffffff; background-color: #ffffff; width: 100%">
          <tbody>
            <tr>
              <td style="direction: ltr; font-size: 0px; padding: 20px 0; text-align: center; vertical-align: top;">
                <!--[if mso | IE]>
                <table role="presentation" border="0" cellpadding="0" cellspacing="0"><tr><td style="vertical-align:top;width:600px;">
                <![endif]-->

                <div class="mj-column-per-100 outlook-group-fix" style="font-size: 13px; text-align: left; direction: ltr; display: inline-block; vertical-align: top; width: 100%;">
                  <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align: top;" width="100%">
                    <tr>
                      <td align="left" style="font-size: 0px; padding: 10px 25px; word-break: break-word;">
                        <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse: collapse; border-spacing: 0px;">
                          <tbody>
                            <tr>
                              <td style="width: 54px; border-radius: 100%; ">
                                <img style=" width: 100%; height: 100%;  border-radius: 20%; transform-origin: center center; transform: scale(1.0); " alt="Mie logo"  height="auto" src="https://iili.io/3DKqndN.jpg" style="border: 0; display: block; outline: none; text-decoration: none; height: auto; width: 100%;" width="24" />
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </td>
                    </tr>

                    <tr>
                      <td align="left" style="font-size: 0px; padding: 10px 25px 24px 25px; word-break: break-word;">
                        <div style="font-family: -apple-system, system-ui, BlinkMacSystemFont; font-size: 15px; font-weight: 300; line-height: 24px; text-align: left; color: #333333;">
                          <h1>We've noticed a new login</h1>
                          <p>Hi ${esc(vars.firstName)} ${esc(vars.lastName)},</p>
                          <p>This is a routine security alert. Someone logged into your Mie account from a new IP address:</p>
                          <p>
                            <strong>Time:</strong> ${esc(vars.time_data)}<br />
                            <strong>IP address:</strong> ${esc(vars.ip_address)}<br />
                            <strong>Location:</strong> ${esc(vars.location)}<br />
                            <strong>More Information:</strong> ${esc(vars.extra_data)}
                          </p>
                          <p>If this was you, you can ignore this alert. If you noticed any suspicious activity on your account, please change your password on your email login and on your account page.</p>
                        </div>
                      </td>
                    </tr>

                    <tr>
                      <td align="left" style="font-size: 0px; padding: 10px 25px; word-break: break-word;">
                        <div style="font-family: -apple-system, system-ui, BlinkMacSystemFont; font-size: 15px; font-weight: 300; line-height: 24px; text-align: left; color: #333333;">
                          So long, and thanks for all the fish,<br />
                          <strong>The Mie Team</strong>
                        </div>
                      </td>
                    </tr>

                    <tr>
                      <td style="font-size: 0px; padding: 10px 25px; word-break: break-word;">
                        <p style="border-top: solid 1px #e8e8e8; font-size: 1; margin: 0px auto; width: 100%;"></p>
                        <!--[if mso | IE]>
                        <table align="center" border="0" cellpadding="0" cellspacing="0" style="border-top: solid 1px #e8e8e8; font-size: 1; margin: 0px auto; width: 550px;" role="presentation" width="550px">
                          <tr><td style="height: 0; line-height: 0">&nbsp;</td></tr>
                        </table>
                        <![endif]-->
                      </td>
                    </tr>

                    <tr>
                      <td align="left" style="font-size: 0px; padding: 10px 25px; word-break: break-word;">
                        <div style="font-family: -apple-system, system-ui, BlinkMacSystemFont; font-size: 12px; font-weight: 300; line-height: 24px; text-align: left; color: #888888;">
                          Somewhere Between Coffee & Code, Quiet Meadows, Earth 00000<br />
                          © 2025 Mie. LLC
                        </div>
                      </td>
                    </tr>

                    <tr>
                      <td align="left" style="font-size: 0px; padding: 10px 25px; word-break: break-word;">
                        <div style="font-family: -apple-system, system-ui, BlinkMacSystemFont; font-size: 12px; font-weight: 300; line-height: 24px; text-align: left; color: #888888;">
                          For questions contact <a href="mailto:support@x.ai" class="footer-link">support@Mie.com.ng</a>
                        </div>
                      </td>
                    </tr>
                  </table>
                </div>

                <!--[if mso | IE]></td></tr></table><![endif]-->
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <!--[if mso | IE]></td></tr></table><![endif]-->
    </div>
  </body>
</html>


`;
}

/**
 * `changing_password_template.py` — vars `$otp_code $email $avatar`.
 * Legacy bug fixed: the template ended mid-div with a bare `</html>`; the open
 * tags are now closed properly (cosmetic only, per email-resend.md).
 */
export function changingPasswordTemplate(vars: {
  otp_code: string;
  email: string;
  avatar: string;
}): string {
  return `
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Here’s the code to reset your password: ${esc(vars.otp_code)}</title>
  <meta name="format-detection" content="email=no" />
  <meta name="format-detection" content="date=no" />
  <style nonce="DoEqAMc5wqGswLpJhSuEWA">
    .awl a { color: #FFFFFF; text-decoration: none; }
    .abml a { color: #000000; font-family: Roboto-Medium, Helvetica, Arial, sans-serif; font-weight: bold; text-decoration: none; }
    .adgl a { color: rgba(0, 0, 0, 0.87); text-decoration: none; }
    .afal a { color: #b0b0b0; text-decoration: none; }

    @media screen and (min-width: 600px) {
      .v2sp { padding: 6px 30px 0px; }
      .v2rsp { padding: 0px 10px; }
    }

    @media screen and (min-width: 600px) {
      .mdv2rw { padding: 40px 40px; }
    }
     .dark-mode-image {
    display: none; /* Hide the dark mode image by default */
  }
  img {
      filter: invert(100%); /* Inverts colors */
      /* You might need brightness, contrast, hue-rotate etc. */
    }

  /* When the user prefers dark mode */
  @media (prefers-color-scheme: dark) {
    .light-mode-image {
      display: none; /* Hide the light mode image */
    }
    .dark-mode-image {
      display: inline-block; /* Show the dark mode image */
    }
  }
  </style>

  <link href="//fonts.googleapis.com/css?family=Google+Sans" rel="stylesheet" type="text/css" nonce="DoEqAMc5wqGswLpJhSuEWA" />
</head>
<body style="margin: 0; padding: 0;" bgcolor="#FFFFFF">

  <table width="100%" height="100%" style="min-width: 348px;" border="0" cellspacing="0" cellpadding="0" lang="en">
    <tr height="32" style="height: 32px;"><td></td></tr>
    <tr align="center">
      <td>
        <div itemscope itemtype="//schema.org/EmailMessage">
          <div itemprop="action" itemscope itemtype="//schema.org/ViewAction">
            <meta itemprop="name" content="Review Activity" />
          </div>
        </div>

        <table border="0" cellspacing="0" cellpadding="0" style="padding-bottom: 20px; max-width: 516px; min-width: 220px;">
          <tr>
            <td width="8" style="width: 8px;"></td>
            <td>
              <div style="background-color: #F5F5F5; direction: ltr; padding: 16px; margin-bottom: 6px;">
                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                  <tbody>
                    <tr>
                      <td style="vertical-align: top;">
                        <img height="20" src="https://www.gstatic.com/accountalerts/email/Icon_recovery_x2_20_20.png" />
                      </td>
                      <td width="13" style="width: 13px;"></td>
                      <td style="direction: ltr;">
                        <span style="font-family: Roboto-Regular, Helvetica, Arial, sans-serif; font-size: 13px; color: rgba(0,0,0,0.54); line-height: 1.6;">
                          Here’s the code to reset your password: ${esc(vars.otp_code)}
                          <a style="text-decoration: none; color: rgba(0,0,0,0.87);">we’ve sent it to ${esc(vars.email)},</a> the address associated with the account requesting the reset.

                        </span>
                        <span style="font-family: Roboto-Regular, Helvetica, Arial, sans-serif; font-size: 13px; color: rgba(0,0,0,0.54); line-height: 1.6;">
                          If you didn’t request this, you can safely ignore this message.
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div style="border-style: solid; border-width: thin; border-color:#dadce0; border-radius: 8px; padding: 40px 20px;" align="center" class="mdv2rw">
              <img class="dark-mode-image" src="https://iili.io/3DBDnYg.png"

     width="90"
     height="50"
     aria-hidden="true"
     style="margin-bottom: 16px; background-color: rgba(0, 0, 0, 1); border-radius: 10%;"
     alt="Mie" />
                   <img class="light-mode-image" src="https://iili.io/3DBDnYg.png"

     width="90"
     height="50"
     aria-hidden="true"
     style="margin-bottom: 16px; background-color: rgba(0, 0, 0, 1); border-radius: 10%;"
     alt="Mie" />
                <div style="font-family: 'Google Sans', Roboto, RobotoDraft, Helvetica, Arial, sans-serif; border-bottom: thin solid #dadce0; color: rgba(0,0,0,0.87); line-height: 32px; padding-bottom: 24px; text-align: center; word-break: break-word;">
                  <div style="font-size: 24px;">${esc(vars.otp_code)}</div>
                  <table align="center" style="margin-top: 8px;">
                    <tr style="line-height: normal;">
                      <td align="right" style="padding-right: 8px;">
                        <img width="20" height="20" style="width: 20px; height: 20px; vertical-align: sub; border-radius: 50%;" src="${safeUrl(vars.avatar)}" alt="avatar" />
                      </td>
                      <td>
                        <a style="font-family: 'Google Sans', Roboto, RobotoDraft, Helvetica, Arial, sans-serif; color: rgba(0,0,0,0.87); font-size: 14px; line-height: 20px;">${esc(vars.email)}</a>
                      </td>
                    </tr>
                  </table>
                </div>

                <div style="font-family: Roboto-Regular, Helvetica, Arial, sans-serif; font-size: 14px; color: rgba(0,0,0,0.87); line-height: 20px; padding-top: 20px; text-align: center;">
                  We got a request from you to change your password so please use the otp and change your password. If this was you, you don’t need to do anything. If not, we’ll help you secure your account.
                </div>
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
`;
}
