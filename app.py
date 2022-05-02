""" Copyright (c) 2020 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
           https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied. 
"""


from requests_oauthlib import OAuth2Session
from webexteamssdk import WebexTeamsAPI
from flask import Flask, render_template, request, redirect, session, url_for
import datetime
import requests
import json
from dotenv import load_dotenv
import os
import time


# load all environment variables
load_dotenv()


AUTHORIZATION_BASE_URL = 'https://api.ciscospark.com/v1/authorize'
TOKEN_URL = 'https://api.ciscospark.com/v1/access_token'
SCOPE = ['spark:people_read','meeting:schedules_read', 'meeting:preferences_read','meeting:participants_read','meeting:transcripts_read']

#initialize variabes for URLs
#REDIRECT_URL must match what is in the integration, but we will construct it below in __main__
# so no need to hard code it here
PUBLIC_URL='http://0.0.0.0:3000'
REDIRECT_URI=""


os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# Initialize the environment
# Create the web application instance
app = Flask(__name__)

app.secret_key = '123456789012345678901234'
api = None


@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/progress')
def ajax_index():
    global i
    i+=20
    print(i)
    return str(i)

# Methods
# Returns location and time of accessing device
def getSystemTimeAndLocation():
    # request user ip
    userIPRequest = requests.get('https://get.geojs.io/v1/ip.json')
    userIP = userIPRequest.json()['ip']

    # request geo information based on ip
    geoRequestURL = 'https://get.geojs.io/v1/ip/geo/' + userIP + '.json'
    geoRequest = requests.get(geoRequestURL)
    geoData = geoRequest.json()
    
    #create info string
    location = geoData['country']
    timezone = geoData['timezone']
    current_time=datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    timeAndLocation = "System Information: {}, {} (Timezone: {})".format(location, current_time, timezone)

    return timeAndLocation

def getSystemTimeStr():
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

def getSystemTimeOnly():
    return datetime.datetime.now().strftime("%H:%M:%S")

#Read data from json file
def getJson(filepath):
	with open(filepath, 'r') as f:
		json_content = json.loads(f.read())
		f.close()

	return json_content

#Write data to json file
def writeJson(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f)
    f.close()


##Routes
#Index
@app.route("/")
def login():
    """Step 1: User Authorization.
    Redirect the user/resource owner to the OAuth provider (i.e. Webex Teams)
    using a URL with a few key OAuth parameters.
    """
    global REDIRECT_URI
    global PUBLIC_URL

    if session.get('oauth_token'):
        tokens = session['oauth_token']
    else:
        tokens = None

    if tokens == None or time.time()>(tokens['expires_at']+(tokens['refresh_token_expires_in']-tokens['expires_in'])):
        # We could not read the token from file or it is so old that even the refresh token is invalid, so we have to
        # trigger a full oAuth flow with user intervention
        REDIRECT_URI = PUBLIC_URL + '/callback'  # Copy your active  URI + /callback
        print("Using PUBLIC_URL: ",PUBLIC_URL)
        print("Using redirect URI: ",REDIRECT_URI)
        teams = OAuth2Session(os.getenv('CLIENT_ID'), scope=SCOPE, redirect_uri=REDIRECT_URI)
        authorization_url, state = teams.authorization_url(AUTHORIZATION_BASE_URL)

        # State is used to prevent CSRF, keep this for later.
        print("Storing state: ", state)
        session['oauth_state'] = state
        print("root route is re-directing to ",authorization_url," and had sent redirect uri: ",REDIRECT_URI)
        return redirect(authorization_url)
    else:
        # We read a token from file that is at least younger than the expiration of the refresh token, so let's
        # check and see if it is still current or needs refreshing without user intervention
        print("Existing token on file, checking if expired....")
        access_token_expires_at = tokens['expires_at']
        if time.time() > access_token_expires_at:
            print("expired!")
            refresh_token = tokens['refresh_token']
            # make the calls to get new token
            extra = {
                'client_id': os.getenv('CLIENT_ID'),
                'client_secret': os.getenv('CLIENT_SECRET'),
                'refresh_token': refresh_token,
            }
            auth_code = OAuth2Session(os.getenv('CLIENT_ID'), token=tokens)
            new_teams_token = auth_code.refresh_token(TOKEN_URL, **extra)
            print("Obtained new_teams_token: ", new_teams_token)
            # assign new token
            tokens = new_teams_token

        session['oauth_token'] = tokens
        print("Using stored or refreshed token....")
        return redirect(url_for('.dashboard'))

@app.route("/logout", methods=["GET"])
def logout():
    session.pop("oauth_token", None)
    session.pop("participants_report", None)
    return redirect("/")

# Step 2: User authorization, this happens on the provider.

@app.route("/callback", methods=["GET"])
def callback():
    """
    Step 3: Retrieving an access token.
    The user has been redirected back from the provider to your registered
    callback URL. With this redirection comes an authorization code included
    in the redirect URL. We will use that to obtain an access token.
    """
    global REDIRECT_URI

    print("Came back to the redirect URI, trying to fetch token....")
    print("redirect URI should still be: ",REDIRECT_URI)
    print("Calling OAuth2SEssion with CLIENT_ID ",os.getenv('CLIENT_ID')," state ",session['oauth_state']," and REDIRECT_URI as above...")
    auth_code = OAuth2Session(os.getenv('CLIENT_ID'), state=session['oauth_state'], redirect_uri=REDIRECT_URI)
    print("Obtained auth_code: ",auth_code)
    print("fetching token with TOKEN_URL ",TOKEN_URL," and client secret ",os.getenv('CLIENT_SECRET')," and auth response ",request.url)
    token = auth_code.fetch_token(token_url=TOKEN_URL, client_secret=os.getenv('CLIENT_SECRET'),
                                  authorization_response=request.url)

    print("Token: ",token)
    print("should have grabbed the token by now!")
    # persist session token
    session['oauth_token'] = token

    return redirect(url_for('.dashboard'))

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if session.get('oauth_token'):
        try:
            # Use returned token to make Teams API calls for information on user, list of spaces and list of messages in spaces
            global api


            # render template and pass all the obtained information
            print(getSystemTimeOnly)
            return render_template('collector_dashboard.html', timeAndLocation=getSystemTimeAndLocation(), sysTime=getSystemTimeStr(), currTime=getSystemTimeOnly())

        except Exception as e: 
            print(e)
            #OR the following to show error message 
            return render_template('collector_dashboard.html', error=False, errormessage="Error loading dashboard. See logs...", errorcode=e, timeAndLocation=getSystemTimeAndLocation(), sysTime=getSystemTimeStr(), currTime=getSystemTimeOnly())
    else:
        return redirect('/')

@app.route("/generate-report", methods=["POST"])
def generate_report():
    token = session['oauth_token']
    headers = {
        'Authorization': 'Bearer ' + token['access_token'],
        'Content-Type': 'application/json',
        "timezone": "GMT"
    }
    start = request.get_json()['from']
    end = request.get_json()['to']
    meetings = retrieve_meetings_sub(start, end)
    # Get all meetings as json and combine into single csv
    # Day field should be auto populated (start time)

    meetingParticipants = {'items': []}
    if meetings:
        for meeting in meetings['items']:
            theMeetingID = meeting['id']
            # list participants of a meeting
            print(f"Getting meeting ({meeting['title']}) participants for meetingId: {theMeetingID}")
            url = "https://webexapis.com/v1/meetingParticipants"
            params = {
                    "meetingId": theMeetingID
            }
            participant = requests.request("GET", url, headers=headers, params=params)
            if participant.ok:

                # add information from the list meetings API to the participants API
                temp_participants = participant.json()['items']

                for temp_participant in temp_participants:
                    temp_participant['meeting_title'] = meeting['title']
                    temp_participant['meeting_start_time'] = meeting['start']
                    temp_participant['meeting_end_time'] = meeting['end']

                meetingParticipants['items'].extend(temp_participants)

    # persist participants-report for user session
    session['participants_report'] = meetingParticipants

    return meetingParticipants

@app.route("/retrieve-meetings", methods=["POST"])
def retrieve_meetings():
    start = request.get_json()['from']
    end = request.get_json()['to']
    return retrieve_meetings_sub(start, end)

def retrieve_meetings_sub(start, end):

    url = "https://webexapis.com/v1/meetings"

    # setup the time constraint variables to specify for events.list
    # need to test start, end params coming front front-end
    fromTime = start
    toTime = end


    token = session['oauth_token']

    print(f'Getting meetings From: {fromTime} To: {toTime}')
    params = {
            "from": fromTime,
            "to": toTime,
            "meetingType": "meeting" #changed from scheduledMeeting
    }
    headers = {
        'Authorization': 'Bearer ' + token['access_token'],
        'Content-Type': 'application/json',
        "timezone": "GMT"
    }

    response = requests.request("GET", url, headers=headers, params=params)
    print(response.text)

    return response.json()

#manual refresh of the token
@app.route('/refresh', methods=['GET'])
def webex_teams_webhook_refresh():
    global api
    teams_token = session['oauth_token']

    # use the refresh token to
    # generate and store a new one
    access_token_expires_at=teams_token['expires_at']

    print("Manual refresh invoked!")
    print("Current time: ",time.time()," Token expires at: ",access_token_expires_at)
    refresh_token=teams_token['refresh_token']
    #make the calls to get new token
    extra = {
        'client_id': os.getenv('CLIENT_ID'),
        'client_secret': os.getenv('CLIENT_SECRET'),
        'refresh_token': refresh_token,
    }
    auth_code = OAuth2Session(os.getenv('CLIENT_ID'), token=teams_token)
    new_teams_token=auth_code.refresh_token(TOKEN_URL, **extra)
    print("Obtained new_teams_token: ", new_teams_token)

    #store new token
    teams_token=new_teams_token
    session['oauth_token'] = teams_token

    #test that we have a valid access token
    api = WebexTeamsAPI(access_token=teams_token['access_token'])

    return ("""<!DOCTYPE html>
                   <html lang="en">
                       <head>
                           <meta charset="UTF-8">
                           <title>Webex Teams Bot served via Flask</title>
                       </head>
                   <body>
                   <p>
                   <strong>The token has been refreshed!!</strong>
                   </p>
                   </body>
                   </html>
                """)

# Start the Flask web server
if __name__ == '__main__':
    print("Using PUBLIC_URL: ",PUBLIC_URL)
    print("Using redirect URI: ",REDIRECT_URI)
    app.run(host='0.0.0.0', port=3000, debug=True)