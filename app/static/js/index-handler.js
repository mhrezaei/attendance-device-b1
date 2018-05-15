//     Advisory messages which show each status on logic.py

//    var zeroth_message = 'Fingerprint is not read yet';
//    var first_message = 'Fingerprint is read';
    var second_message = 'No match found!';
//    var third_message = 'Found template at position # + str(position_number)';
//    var fourth_message = 'The accuracy score is: + str(accuracy_score)';
//    var fifth_message = 'Finger does NOT exist!';
//    var sixth_message = 'Finger exists!';
//    var seventh_message = 'SHA-2 hash of template: + hashlib.sha256(characterics).hexdigest()';
//    var eighth_message = 'The user_id is: + str(the_user_id)';
//    var ninth_message = 'The user_logs table does NOT have this user_id. Inserting the record.';
//    var tenth_message = 'exited_at field is NOT empty!';
//    var eleventh_message = 'Inserting NEW fresh record in the table.';
//    var twelfth_message = 'exited_at field is empty!';
//    var thirteenth_message = 'the_very_last_entered_at: + str(the_very_last_entered_at)';
//    var fourteenth_message = 'More than 60 seconds spent from this finger scan!';
    var fifteenth_message = 'Welcome ';
//    var sixteenth_message = 'Less than 60 seconds spent from this finger scan!';
    var seventeenth_message = 'Goodbye ';
    var eighteenth_message = 'attendance_not_allowed has not passed. NOT ready to apply user log.';
//    var nineteenth_message = 'no_action_allowed has passed. Ready to apply user log.';
    var twentieth_message = 'This user is not active anymore.';
    var thirty_one = 'Successful log for this RFID card inserted in the database.';
    var thirty_two = 'attendance_not_allowed has not passed. NOT ready to apply user log.';

    $(document).ready(function () {
        var connected = false;
        var key = null;
        const socket = io('http://' + document.domain + ':' + location.port);

        socket.on('connect', function () {
            $('#status').text("Connected.");
            connected = true;
        });

        socket.on('auth', function (data) {
            $('#auth').text(data);
            socket.emit('setFingerPrintStatus', true);
        });


        socket.on('fingerPrintStatus', function (data) {
            if (data.status <= 2) {
                $('#message').text(second_message).fadeIn("slow", function() { $(this).delay(3000).fadeOut("slow"); });
            }
            if (data.status >= 3 && data.status <= 15) {
                $('#message').text(fifteenth_message + data.first_name + ' ' + data.last_name + ', your last exit: ' + data.last_action).fadeIn("slow", function() { $(this).delay(3000).fadeOut("slow"); });
            }
            if (data.status >= 16 && data.status <= 17) {
                $('#message').text(seventeenth_message + data.first_name + ' ' + data.last_name + ', your last enter: ' + data.last_action).fadeIn("slow", function() { $(this).delay(3000).fadeOut("slow"); });
            }
            if (data.status == 18) {
                $('#message').text(eighteenth_message).fadeIn("slow", function() { $(this).delay(3000).fadeOut("slow"); });
            }
            if (data.status == 20) {
                $('#message').text(twentieth_message).fadeIn("slow", function() { $(this).delay(3000).fadeOut("slow"); });
            }
            if (data.status == 31) {
                $('#message').text(thirty_one).fadeIn("slow", function() { $(this).delay(3000).fadeOut("slow"); });
            }
            if (data.status == 32) {
                $('#message').text(thirty_two).fadeIn("slow", function() { $(this).delay(3000).fadeOut("slow"); });
            }
        });

        socket.on('disconnect', function () {
            console.log('disconnected.');
            connected = false;
            $('#status').text("Disconnected.");
        });

        setInterval(function () {
            if (connected)
                socket.emit('update');
        }, 500);

    });