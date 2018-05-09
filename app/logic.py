from time import sleep, time
from datetime import datetime, timedelta
from config import store, socket, publish, fingerprint, db, User, UserLog
import hashlib

store['fingerPrintEnabled'] = False

def receive(action, message):
    if action == 'fingerPrintStatus':
        print(message)
        socket.emit('fingerPrintStatus', message, broadcast=True)
    pass


def run():
    if store['fingerPrintEnabled']: #boolean
        # sleep(0.5) #TODO: 1 second or not
        our_result = {'status': 0, 'first_name': '', 'last_name': '', 'last_action': ''}
        if fingerprint.readImage() != 0:
            fingerprint.convertImage(0x01)
            # Searches template
            result = fingerprint.searchTemplate()

            position_number = result[0]
            accuracy_score = result[1]

            # If finger match was NOT found
            if position_number == -1:
                # flash('No match found!')
                our_result['status'] = 2
                publish('fingerPrintStatus', our_result)
            # If finger match was found
            elif position_number != -1:
                # flash('Found template at position #' + str(position_number))
                our_result['status'] = 3
                # flash('The accuracy score is: ' + str(accuracy_score))
                our_result['status'] = 4
                # Executing Queries
                template_position_existence_clause = db.table('fingers').where('template_position', position_number).count()
                # Check if it is the Admin's Finger for going to Settings #TODO: add user role: admin and check it this way

                # If the user_id does NOT exist in the fingers table
                if template_position_existence_clause == 0:
                    # flash('Finger does NOT exist!')
                    our_result['status'] = 5
                    # time.sleep(3)
                    # return redirect('activate')
                    publish('fingerPrintStatus', our_result)

                # If the user_id exists in the fingers table
                elif template_position_existence_clause != 0:
                    # flash('Finger exists!')
                    our_result['status'] = 6
                    # Loads the found template to char buffer 1
                    fingerprint.loadTemplate(position_number, 0x01)

                    # Downloads the characteristics of template loaded in char buffer 1
                    characterics = str(fingerprint.downloadCharacteristics(0x01)).encode('utf-8')

                    # Hashes characteristics of template
                    # flash('SHA-2 hash of template: ' + hashlib.sha256(characterics).hexdigest())
                    our_result['status'] = 7

                    the_user_id = db.table('fingers').where('template_position', int(position_number)).pluck(
                        'user_id')
                    the_first_name = db.table('users').where('id', the_user_id).pluck('first_name')
                    the_last_name = db.table('users').where('id', the_user_id).pluck('last_name')
                    # Now we have the user_id associated with the template_position
                    # flash('The user_id is: ' + str(the_user_id))
                    our_result['status'] = 8

                    our_result['first_name'] = the_first_name
                    our_result['last_name'] = the_last_name
                    # print(our_result)

                    user_id_existence_clause_2 = db.table('user_logs').where('user_id', the_user_id).order_by('id',
                                                                                                              'desc').pluck(
                        'id')
                    # b = cur.execute(
                    #     """SELECT * FROM `user_logs` WHERE `user_id`='%d' ORDER BY id DESC LIMIT 1""" % (int(the_user_id)))
                    # The user_logs table does NOT have this user_id, inserting the first record of this user_id
                    if user_id_existence_clause_2 is None:
                        # flash('The user_logs table does NOT have this user_id. Inserting the record.')
                        the_template_position = position_number
                        the_entered_at = datetime.now()  # time right now
                        the_hash = hashlib.sha256(characterics).hexdigest()
                        the_accuracy = accuracy_score
                        # cur.execute(
                        #     """INSERT INTO `user_logs` (`user_id`, `template_position`, `entered_at`, `hash`, `accuracy`) VALUES ('%d', '%d', '%s', '%s', '%s')"""
                        #     % (int(the_user_id), int(the_template_position), str(the_entered_at), str(the_hash), str(the_accuracy)))
                        db.table('user_logs').insert(user_id=the_user_id, template_position=the_template_position,
                                                     entered_at=the_entered_at, hash=the_hash,
                                                     accuracy=the_accuracy)

                        our_result['last_action'] = 'You have no records yet.'
                        # time.sleep(3)
                        # return redirect('activate')
                        publish('fingerPrintStatus', our_result)


                    # The user_logs table has this user_id
                    elif user_id_existence_clause_2 is not None:
                        # Retrieve the exited_at associated with the template_position from the fingers table
                        the_exited_at = db.table('user_logs').where('user_id', the_user_id).order_by('id',
                                                                                                     'desc').pluck(
                            'exited_at')

                        # exited_at field is NOT empty
                        if the_exited_at is not None:
                            # flash('exited_at field is NOT empty!')
                            our_result['status'] = 10
                            # flash('Inserting NEW record.')
                            our_result['status'] = 11
                            # time.sleep(3)
                            the_template_position = position_number
                            the_entered_at = datetime.now()  # time right now
                            the_hash = hashlib.sha256(characterics).hexdigest()
                            the_accuracy = accuracy_score

                            the_very_last_exited_at = db.table('user_logs').where('user_id', the_user_id).order_by(
                                'id',
                                'desc').pluck(
                                'exited_at')

                            our_result['last_action'] = str(the_very_last_exited_at)

                            db.table('user_logs').insert(user_id=the_user_id,
                                                         template_position=the_template_position,
                                                         entered_at=the_entered_at, hash=the_hash,
                                                         accuracy=the_accuracy)
                            # time.sleep(3)
                            # return redirect('activate')
                            publish('fingerPrintStatus', our_result)

                        # exited_at field is empty
                        elif the_exited_at is None:
                            # flash('exited_at field is empty!')
                            our_result['status'] = 12

                            # Retrieve the entered_at associated with the template_position from the fingers table
                            the_very_last_entered_at = db.table('user_logs').where('user_id', the_user_id).order_by(
                                'id',
                                'desc').pluck(
                                'entered_at')

                            # print(type(the_very_last_entered_at))
                            our_result['status'] = 13
                            temp_time = the_very_last_entered_at + timedelta(
                                seconds=60)  # TODO: Make it a dynamic variable
                            # pprint(temp_time)
                            # flash('temp_time: ' + str(temp_time))
                            the_new_entered_at = datetime.now()  # time right now

                            # More than specified time spent from this finger scan
                            if the_new_entered_at > temp_time:
                                # flash('More than 60 seconds spent from this finger scan!')
                                our_result['status'] = 14
                                # flash('It is a NEW ENTER!')
                                our_result['status'] = 15

                                # time.sleep(3)
                                the_template_position = position_number
                                the_hash = hashlib.sha256(characterics).hexdigest()
                                the_accuracy = accuracy_score

                                our_result['last_action'] = ''

                                db.table('user_logs').insert(user_id=the_user_id,
                                                             template_position=the_template_position,
                                                             entered_at=the_new_entered_at, hash=the_hash,
                                                             accuracy=the_accuracy)
                                # our_result['last_action'] =
                                # time.sleep(3)
                                # return redirect('activate')
                                publish('fingerPrintStatus', our_result)

                            # Less than specified times spent from this finger scan
                            else:
                                # flash('Less than 60 seconds spent from this finger scan!')
                                our_result['status'] = 16
                                # flash('It is an EXIT!')
                                our_result['status'] = 17
                                # time.sleep(3)
                                the_exited_at = datetime.now()  # time right now

                                db.table('user_logs').where('entered_at', the_very_last_entered_at).update(
                                    exited_at=the_exited_at)

                                our_result['last_action'] = str(the_very_last_entered_at)
                                # time.sleep(3)
                                # return redirect('activate')
                                publish('fingerPrintStatus', our_result)
    else:
        sleep(1)
