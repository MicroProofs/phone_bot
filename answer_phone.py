import re
from flask import flash, render_template, redirect, request, session, url_for, Flask
from twilio.rest.pricing.v1.voice.number import NumberInstance

from twilio.twiml.voice_response import VoiceResponse
import flask as FlaskM
import os
from twilio.rest import Client
import tabulate

# Find your Account SID and Auth Token at twilio.com/console
# and set the environment variables. See http://twil.io/secure

app = Flask(__name__)


def twiml(resp: VoiceResponse):
    resp = FlaskM.Response(str(resp))
    resp.headers["Content-Type"] = "text/xml"
    return resp


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/call_conversion_logs/<phone_number>/<date>", methods=["GET"])
def get_call_logs(phone_number: str, date: str):
    final_string = "<h3>If under 65 we only need to check if interested in a policy. If over 65 we need to check if they have plan B Medicare</h3><br><br>"
    table_rows = []
    calls = client.calls.list(start_time=date, to="+1" + phone_number, page_size=1000)
    for record in calls:
        id = record.sid[-7:]
        number = record.from_[2:]
        print(record.sid)
        print(record.from_)
        events = client.calls(record.sid).events.list(page_size=1000)
        age = _check_events_urlpath_and_digits("age", events)
        interested = None
        planb = None
        qualified = "false"
        converted = "pending"
        if age and age == "1":
            interested = _check_events_urlpath_and_digits("interested", events)
            if interested and interested == "1":
                qualified = "true"
        if age and age == "2":
            planb = _check_events_urlpath_and_digits("planb", events)
            if planb and planb == "1":
                qualified = "true"

        table_rows.append([id, number, str(age and age == "1"), str(planb and planb == "1"), qualified, converted])

    final_string += tabulate.tabulate(
        tabular_data=table_rows,
        headers=["|id|", "|phone number|", "|over 65|", "|plan b if over 65|", "|qualified|", "|converted|"],
        tablefmt="html",
    )
    return final_string


@app.route("/welcome", methods=["POST"])
def welcome():
    response = VoiceResponse()
    with response.gather(num_digits=1, action=url_for("age"), method="POST") as g:
        g.say(
            message="Thank you for calling Medasurance!. Before we connect you with an agent,,,, please answer one quick question......",
            voice="Polly.Joanna",
            rate="85%",
        )
        g.pause()
        g.say(message="Are you over 65 years old??? Press 1 for yes.. Press 2 for no..", voice="Polly.Joanna", rate="85%")

    with response.gather(num_digits=1, action=url_for("age"), method="POST") as g:
        g.say(message="Are you over 65 years old??? Press 1 for yes.. Press 2 for no..", loop=1, voice="Polly.Joanna", rate="85%")

    response.redirect("end")
    return twiml(response)


@app.route("/end", methods=["POST"])
def end():
    response = VoiceResponse()
    response.say("Goodbye")
    response.hangup()
    return twiml(response)


@app.route("/age", methods=["POST"])
def age():
    selected_option = request.form["Digits"]
    option_actions = {"1": _ask_planb, "2": _hang_up}

    if selected_option in option_actions.keys():
        response = VoiceResponse()
        option_actions[selected_option](response)
        return twiml(response)
    else:
        response = VoiceResponse()
        return _hang_up(response)


@app.route("/interested", methods=["POST"])
def interested():
    selected_option = request.form["Digits"]
    option_actions = {"1": _convert_not_senior, "2": _hang_up}

    if selected_option in option_actions.keys():
        response = VoiceResponse()
        option_actions[selected_option](response)
        return twiml(response)
    else:
        response = VoiceResponse()
        return _hang_up(response)


@app.route("/planb", methods=["POST"])
def planb():
    selected_option = request.form["Digits"]
    option_actions = {"1": _convert_senior, "2": _hang_up}

    if selected_option in option_actions.keys():
        response = VoiceResponse()
        option_actions[selected_option](response)
        return twiml(response)
    else:
        response = VoiceResponse()
        return _hang_up(response)


# private methods
def _hang_up(response: VoiceResponse):
    response.say("I am sorry, at this time we do not have any available reps.", voice="Polly.Joanna")
    response.hangup()
    return response


def _ask_interest(response: VoiceResponse):
    with response.gather(numDigits=1, action=url_for("interested"), method="POST") as g:
        g.say(
            "While we get an agent on the line,,, Are you looking for an active policy as soon as possible? Press 1 for Yes... Press 2 for No...",
            voice="Polly.Joanna",
            rate="85%",
        )

    with response.gather(numDigits=1, action=url_for("interested"), method="POST") as g:
        g.say(
            "While we get an agent on the line,,, Are you looking for an active policy as soon as possible? Press 1 for Yes... Press 2 for No...",
            voice="Polly.Joanna",
            rate="85%",
        )
    response.redirect("end")
    return response


def _ask_planb(response: VoiceResponse):
    with response.gather(numDigits=1, action=url_for("planb"), method="POST") as g:
        g.say(
            "While we get an agent on the line,,, Are you signed up for Part B Medicare? Press 1 for Yes... Press 2 for No...",
            voice="Polly.Joanna",
            rate="85%",
        )

    with response.gather(numDigits=1, action=url_for("planb"), method="POST") as g:
        g.say(
            "While we get an agent on the line,,, Are you signed up for Part B Medicare? Press 1 for Yes.... Press 2 for No...",
            voice="Polly.Joanna",
            loop=1,
        )
    response.redirect("end")
    return response


def _convert_not_senior(response: VoiceResponse):
    response.hangup()
    # response.dial("+12024173378")
    return twiml(response)


def _convert_senior(response: VoiceResponse):
    response.dial("+18885971052")
    return twiml(response)


def _check_events_urlpath_and_digits(urlpath, events):
    path_request = list(filter(lambda e: urlpath in e.request["url"], events))
    digits = None
    if len(path_request) > 0:
        digits = path_request[0].request["parameters"]["digits"]

    return digits


if __name__ == "__main__":
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    client = Client(account_sid, auth_token)
    app.run(debug=True)