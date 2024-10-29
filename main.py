from flask import Flask, redirect, render_template, flash, request, url_for, jsonify
import db

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True
app.config['SECRET_KEY'] = 'momoeqw i0305 woiuqwhogfw'

# Routing


@app.route("/")
def root():
    return redirect("/login")


@app.route("/getloc")
def getloc():
    user_id = request.args.get('user_id')
    return render_template("getloc.html", user_id=user_id)


@app.route("/talksnearyou")
def talksnearyou():
    return render_template("talksnearyou.html")


@app.route("/hostsettings")
def hostsettings():
    return render_template("hostsettings.html")


@app.route("/showparticipants")
def showparticipants():
    user_id = request.args.get('user_id')
    talk_id = request.args.get('talk_id')
    return render_template('showparticipants.html', user_id=user_id, talk_id=talk_id)


@app.route('/on_the_way')
def on_the_way():
    user_id = request.args.get('user_id')
    talk_id = db.get_talk_by_user(user_id)
    talk_title = db.get_talk_topic(db.get_talk_by_user(user_id))
    return render_template('ontheway.html', user_id=user_id, talk_title=talk_title, talk_id=talk_id)


@app.route("/finalpage")
def finalpage():
    user_id = request.args.get('user_id')
    talk_id = request.args.get('talk_id')
    users = db.get_all_attendees(talk_id)
    return render_template("finalpage.html", user_id=user_id, users=users)


@app.route("/start")
def start():
    return render_template("start.html")

# API calls


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        # check user_id existence
        user_id = db.find_user_id_by_name(username)
        if user_id:
            # if the user exists
            if db.check_password(user_id, password):
                flash("Login successful")
                return redirect(url_for('getloc', user_id=user_id))
            else:
                flash(("Invalid password"))
                return redirect("/")
        else:
            # if the user does not exist
            # create user and return user_id
            user_id = db.create_user(username, password)
            flash("New User Created")
            return redirect("/")
            
    return render_template("login.html")


@app.route("/getloc", methods=['POST'])
def getLoc():
    data = request.json  # Get the JSON data sent from the client
    user_id = data.get('user_id')
    id_is_valid = db.find_user_name_by_id(user_id)
    if not id_is_valid:
        return jsonify("error: user_id invalid.", 404)
    
    lat = data.get('latitude')
    lon = data.get('longitude')

    db.set_location(user_id, lat, lon)

    # do whatever you need w/ coords
    return redirect(url_for('start', user_id=user_id))


@app.route('/create-talk', methods=['POST'])
def createTalk():
    data = request.json  # Get the JSON data sent from the client
    topic = data.get('topic')
    max_size = data.get('max_size')
    host_id = data.get('user_id')
    id_is_valid = db.find_user_name_by_id(host_id)
    if not id_is_valid:
        return "error: user_id invalid.", 404
        
    loc = db.get_location(host_id)

    # Create a talk
    try:
        db.create_talk(topic, max_size, host_id, loc)
        return jsonify({'success': True, 'talk_id': str(db.get_talk_by_user(host_id))}), 200, {'ContentType': 'application/json'}
    except Exception as e:
        return e, 500


@app.route('/get-attendees', methods=['POST'])
def getAttendees():
    data = request.json  # Get the JSON data sent from the client
    user_id = data.get('user_id')
    id_is_valid = db.find_user_name_by_id(user_id)
    if not id_is_valid:
        return "error: user_id invalid.", 404

    talk_id = db.get_talk_by_user(user_id)
    attendees = db.get_all_attendees(talk_id)
    if attendees:
        return jsonify(attendees), 200
    else:
        return jsonify({'message': 'No attendees.'}), 404


@app.route('/host-cancel', methods=['POST'])
def hostCancel():
    try:
        data = request.json  # Get the JSON data sent from the client
        user_id = data.get('user_id')
        id_is_valid = db.find_user_name_by_id(user_id)
        if not id_is_valid:
            return "error: user_id invalid.", 404

        talk_id = str(db.get_talk_by_user(user_id))
        delete_result = db.host_cancel(talk_id)
        return redirect(url_for('start', user_id=user_id))
    except Exception as e:
        return e, 500


@app.route('/host-done', methods=['POST'])
def hostDone():
    try:
        data = request.json  # Get the JSON data sent from the client
        user_id = data.get('user_id')
        id_is_valid = db.find_user_name_by_id(user_id)
        if not id_is_valid:
            return "error: user_id invalid.", 404

        talk_id = str(db.get_talk_by_user(user_id))
        db.host_done(talk_id)
        print("================____++++++++++++______===============")
        print("host_done")
        return redirect(url_for('finalpage', user_id=user_id))
    except Exception as e:
        return e, 500


@app.route('/show-near-talks', methods=['POST'])
def showNearTalks():
    user_id = request.json.get('user_id')
    id_is_valid = db.find_user_name_by_id(user_id)
    if not id_is_valid:
        return "error: user_id invalid.", 404

    loc = db.get_location(user_id)
    lat = loc['lat']
    long = loc['lon']
    nearest_talks = db.find_nearest_talks(lat, long)
    return jsonify(nearest_talks)  # Return talks as JSON


@app.route('/select-talk', methods=['POST'])
def select_talk():
    user_id = request.json.get('user_id')
    id_is_valid = db.find_user_name_by_id(user_id)
    if not id_is_valid:
        return "error: user_id invalid.", 404

    talk_id = request.json.get('talk_id')

    # Here you would implement logic to handle the selected talk, e.g., save to database, etc.
    db.user_join_talk(talk_id, user_id)

    # Redirect to the ontheway page
    return redirect(url_for('on_the_way', user_id=user_id))


@app.route('/update-message', methods=['POST'])
def updateMessage():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        id_is_valid = db.find_user_name_by_id(user_id)
        if not id_is_valid:
            return "error: user_id invalid.", 404

        message = data.get('message')
        # Process the message update logic here
        talk_id = str(db.get_talk_by_user(user_id))
        result = db.attendee_update_message(talk_id, user_id, message)
        print("================+++++++++++++===============++++++++++++++")
        print(result)
        return jsonify({'status': 'success', 'user_id': user_id, 'message': message}), 200
    except Exception as e:
        return e, 500


@app.route('/attendee-arrive', methods=['POST'])
def attendeeArrive():
    try:
        user_id = request.json.get('user_id')
        id_is_valid = db.find_user_name_by_id(user_id)
        if not id_is_valid:
            return "error: user_id invalid.", 404

        # Handle attendee arrival logic here
        talk_id = str(db.get_talk_by_user(user_id))
        db.attendee_arrive(talk_id, user_id)
        return jsonify({'status': 'success', 'user_id': user_id}), 200
    except Exception as e:
        return e, 500


@app.route('/attendee-cancel', methods=['POST'])
def attendeeCancel():
    try:
        user_id = request.json.get('user_id')
        id_is_valid = db.find_user_name_by_id(user_id)
        if not id_is_valid:
            return "error: user_id invalid.", 404

        # Handle attendee cancellation logic here
        talk_id = str(db.get_talk_by_user(user_id))
        db.attendee_cancel(talk_id, user_id)        
        return jsonify({'status': 'success', 'user_id': user_id})
    except Exception as e:
        return e, 500


@app.route('/check-talk-status', methods=['GET', 'POST'])
def checkTalkStatus():
    user_id = request.json.get('user_id')
    try:
        id_is_valid = db.find_user_name_by_id(user_id)
        if not id_is_valid:
            return "error: user_id invalid.", 404

        talk_id = str(db.get_talk_by_user(user_id))
        # Handle attendee arrival logic here
        status = db.get_talk_status(talk_id)
        return jsonify({'talk_status': status})
    except Exception as e:
        return jsonify({'talk_status': cancelled})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port='3060', debug=True)
