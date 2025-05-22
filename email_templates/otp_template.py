from string import Template

otp_template_string=Template("""
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
                                <p>$otp_code</p>
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
                                <img  style="width: 50px; height: 50px; border-radius: 25%; margin-top:10px ;"  src="https://res.cloudinary.com/dfmzougki/image/upload/fl_preserve_transparency/v1747719299/Mie-logo_sfv8nl.jpg?_s=public-apps" alt=
="Mie Logo"/>
                                <p style="padding: 0 22px">Mie. All rights reserved.</p>
                                <div class="footer-text">
                                    This email was intended for <span class=
="user-email">$user_email</span>. This message
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

""")

def generate_login_otp_email_from_template(otp_code,user_email):
    generated_email = otp_template_string.substitute(otp_code=otp_code,user_email=user_email)
    return generated_email