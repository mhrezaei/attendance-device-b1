from time import sleep, time
from datetime import datetime, timedelta

from serial import SerialException

from config import store, socket, publish, fingerprint, db, User, UserLog
import hashlib
from globla_variables import working_hours
from globla_variables import attendance_not_allowed_timeout
import RPi.GPIO as GPIO
import SimpleMFRC522
import os
import spi

store['fingerPrintEnabled'] = False
store['rfidEnabled'] = False

def receive(action, message):
    if action == 'fingerPrintStatus':
        print(message)
        socket.emit('fingerPrintStatus', message, broadcast=True)
    pass


def run_fingerprint():
    if store['fingerPrintEnabled']: #boolean
        # sleep(0.5) #TODO: 1 second or not
        our_result = {'status': 0, 'first_name': '', 'last_name': '', 'last_action': ''}
        the_flag = 0
        the_device = 'fingerprint'

        # read_image = None
        try:
            read_image = fingerprint.readImage()
            if read_image != 0:
                finger_read_time = int(time())

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
                if position_number != -1:
                    print('Found Template')
                    fingerprint.loadTemplate(position_number, 0x01)
                    characterics = str(fingerprint.downloadCharacteristics(0x01)).encode('utf-8')
                    # sleep(2)
                    # flash('Found template at position #' + str(position_number))
                    our_result['status'] = 3
                    # flash('The accuracy score is: ' + str(accuracy_score))
                    our_result['status'] = 4

                    user_related_with_this_finger = db.table('fingers').where('template_position', position_number).pluck('user_id')
                    is_active_clause = db.table('users').where('id', user_related_with_this_finger).pluck('is_active')

                    if is_active_clause == 0:  # This user is NOT active
                        our_result['status'] = 20
                        publish('fingerPrintStatus', our_result)
                        sleep(2)

                    elif is_active_clause != 0:  # This user is active

                        user_related_with_this_finger = db.table('fingers').where('template_position', position_number).pluck('user_id')
                        this_user_last_effect = db.table('user_logs').where('user_id', user_related_with_this_finger).order_by('id', 'desc').pluck('effected_at')

                        if this_user_last_effect is None: # This user has no records in the table yet. It's a fresh record.
                            the_user_id = user_related_with_this_finger
                            the_effected_at = datetime.now()
                            the_type = 'normal_in' #@TODO: Must be dynamic later.
                            the_template_position = position_number
                            the_hash = hashlib.sha256(characterics).hexdigest()
                            the_accuracy = accuracy_score

                            the_first_name = db.table('users').where('id', user_related_with_this_finger).pluck('first_name')
                            the_last_name = db.table('users').where('id', user_related_with_this_finger).pluck('last_name')

                            our_result['first_name'] = the_first_name
                            our_result['last_name'] = the_last_name
                            our_result['last_action'] = 'None'

                            db.table('user_logs').insert(flag=the_flag,
                                                         user_id=the_user_id,
                                                         effected_at=the_effected_at,
                                                         type=the_type,
                                                         device=the_device,
                                                         template_position=the_template_position,
                                                         hash=the_hash,
                                                         accuracy=the_accuracy)
                            publish('fingerPrintStatus', our_result) #@TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                            sleep(2)

                        if this_user_last_effect is not None: # This user already has a record in the table.
                            last_effect_type = db.table('user_logs').where('user_id', user_related_with_this_finger).order_by('id', 'desc').pluck('type')

                            if last_effect_type == 'normal_in':
                                this_finger_last_attendance_action = int(this_user_last_effect.strftime('%s'))  # Converted to epoch
                                check_time = int(this_finger_last_attendance_action + attendance_not_allowed_timeout)

                                if finger_read_time < check_time:  # attendance_not_allowed_timeout has NOT passed. NOT ready to apply user log.
                                    our_result['status'] = 18
                                    # flash('attendance_not_allowed_timeout has NOT passed.')
                                    # print('STATUS 18 - NOT allowed to apply user log.')
                                    publish('fingerPrintStatus', our_result)
                                    sleep(2)

                                elif finger_read_time >= check_time:  # attendance_not_allowed_timeout has passed. Ready to apply user log.
                                    # print('STATUS 19 - Allowed to apply user log.')
                                    the_first_name = db.table('users').where('id', user_related_with_this_finger).pluck('first_name')
                                    the_last_name = db.table('users').where('id', user_related_with_this_finger).pluck('last_name')

                                    the_very_last_normal_in_effected_at = db.table('user_logs').where('user_id', user_related_with_this_finger).where('type', 'normal_in').order_by('id', 'desc').pluck('effected_at')

                                    # the_very_last_normal_in_effected_at_epoch = int(the_very_last_normal_in_effected_at.strftime('%s'))  # Converted to epoch

                                    check_working_hours_time = the_very_last_normal_in_effected_at + timedelta(seconds=working_hours)

                                    the_new_effected_at = datetime.now()  # time right now

                                    # More than specified time spent from this finger scan
                                    if the_new_effected_at > check_working_hours_time:
                                        our_result['status'] = 8

                                        our_result['first_name'] = the_first_name
                                        our_result['last_name'] = the_last_name
                                        our_result['last_action'] = str(the_very_last_normal_in_effected_at)


                                        the_user_id = user_related_with_this_finger
                                        the_effected_at = the_new_effected_at
                                        the_type = 'normal_in'
                                        the_template_position = position_number
                                        the_hash = hashlib.sha256(characterics).hexdigest()
                                        the_accuracy = accuracy_score

                                        db.table('user_logs').insert(flag=the_flag,
                                                                     user_id=the_user_id,
                                                                     effected_at=the_effected_at,
                                                                     type=the_type,
                                                                     device=the_device,
                                                                     template_position=the_template_position,
                                                                     hash=the_hash,
                                                                     accuracy=the_accuracy)
                                        publish('fingerPrintStatus', our_result)  # @TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                                        sleep(2)


                                    elif the_new_effected_at <= check_working_hours_time:
                                        our_result['status'] = 8

                                        our_result['first_name'] = the_first_name
                                        our_result['last_name'] = the_last_name
                                        our_result['last_action'] = str(the_very_last_normal_in_effected_at)

                                        the_user_id = user_related_with_this_finger
                                        the_effected_at = datetime.now()
                                        the_type = 'normal_out'  # @TODO: Must be dynamic later.
                                        the_template_position = position_number
                                        the_hash = hashlib.sha256(characterics).hexdigest()
                                        the_accuracy = accuracy_score


                                        db.table('user_logs').insert(flag=the_flag,
                                                                     user_id=the_user_id,
                                                                     effected_at=the_effected_at,
                                                                     type=the_type,
                                                                     device=the_device,
                                                                     template_position=the_template_position,
                                                                     hash=the_hash,
                                                                     accuracy=the_accuracy)
                                        publish('fingerPrintStatus', our_result)  # @TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                                        sleep(2)


                            elif last_effect_type == 'normal_out':
                                this_finger_last_attendance_action = int(this_user_last_effect.strftime('%s'))  # Converted to epoch
                                check_time = int(this_finger_last_attendance_action + attendance_not_allowed_timeout)

                                the_very_last_normal_in_effected_at = db.table('user_logs').where('user_id', user_related_with_this_finger).where('type', 'normal_in').order_by('id', 'desc').pluck('effected_at')


                                if finger_read_time < check_time:  # attendance_not_allowed_timeout has NOT passed. NOT ready to apply user log.
                                    our_result['status'] = 18
                                    # flash('attendance_not_allowed_timeout has NOT passed.')
                                    # print('STATUS 18 - NOT allowed to apply user log.')
                                    publish('fingerPrintStatus', our_result) # @TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                                    sleep(2)

                                elif finger_read_time >= check_time:  # attendance_not_allowed_timeout has passed. Ready to apply user log.
                                    # print('STATUS 19 - Allowed to apply user log.')
                                    the_first_name = db.table('users').where('id', user_related_with_this_finger).pluck('first_name')
                                    the_last_name = db.table('users').where('id', user_related_with_this_finger).pluck('last_name')
                                    # Now we have the user_id associated with the template_position
                                    # flash('The user_id is: ' + str(the_user_id))
                                    our_result['status'] = 8

                                    our_result['first_name'] = the_first_name
                                    our_result['last_name'] = the_last_name
                                    our_result['last_action'] = str(the_very_last_normal_in_effected_at)

                                    the_user_id = user_related_with_this_finger
                                    the_effected_at = datetime.now()
                                    the_type = 'normal_in'  # @TODO: Must be dynamic later.
                                    the_template_position = position_number
                                    the_hash = hashlib.sha256(characterics).hexdigest()
                                    the_accuracy = accuracy_score

                                    db.table('user_logs').insert(flag=the_flag,
                                                                 user_id=the_user_id,
                                                                 effected_at=the_effected_at,
                                                                 type=the_type,
                                                                 device=the_device,
                                                                 template_position=the_template_position,
                                                                 hash=the_hash,
                                                                 accuracy=the_accuracy)
                                    publish('fingerPrintStatus', our_result)  # @TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                                    sleep(2)

        except KeyboardInterrupt:
            print(' * Terminating... ')
            os.system('kill -9 %d' % os.getpid())

        except SerialException:
            print('Serial Exception happened.')

        except Exception as e:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)
            print(message)


    else:
        sleep(1)


def run_rfid():
    if store['rfidEnabled']:  # boolean
        our_result = dict()
        our_result['status'] = 30
        our_result['message'] = 'Nothing done yet.'
        sleep(1)
        reader = SimpleMFRC522.SimpleMFRC522()
        try:
            unique_id, rfid_owner_user_id = reader.read_no_block()

            if unique_id is not None: # Detected RFID card.
                print('RFID is read.')
                rfid_read_time = time()
                unique_id = str(unique_id)
                print(unique_id)
                print(rfid_owner_user_id)

                unique_id_existence_clause = db.table('rfid_cards').where('unique_id', unique_id).count()

                if unique_id_existence_clause: # This RFID card is registered in the rfid_cards table.

                    user_related_with_this_rfid_card = db.table('rfid_cards').where('unique_id', unique_id).pluck('user_id')

                    the_first_name = db.table('users').where('id', user_related_with_this_rfid_card).pluck('first_name')
                    the_last_name = db.table('users').where('id', user_related_with_this_rfid_card).pluck('last_name')
                    is_active = db.table('users').where('id', user_related_with_this_rfid_card).pluck('is_active')

                    if is_active == 0: # This user is NOT active anymore.
                        our_result['status'] = 34
                        # flash('This user is not active anymore.')
                        publish('fingerPrintStatus', our_result)

                    elif is_active != 0: # This user is active.

                        this_rfid_last_attendance_action = 0

                        this_rfid_last_enter = db.table('user_logs').where('user_id', user_related_with_this_rfid_card).order_by('id', 'desc').pluck('entered_at')
                        if this_rfid_last_enter is not None:
                            this_rfid_last_enter = int(this_rfid_last_enter.strftime('%s'))  # Converted to epoch
                            this_rfid_last_attendance_action = this_rfid_last_enter

                        this_rfid_last_exit = db.table('user_logs').where('user_id', user_related_with_this_rfid_card).order_by('id','desc').pluck('exited_at')
                        if this_rfid_last_exit is not None:
                            this_rfid_last_exit = int(this_rfid_last_exit.strftime('%s'))  # Converted to epoch
                            if this_rfid_last_exit > this_rfid_last_enter:
                                this_rfid_last_attendance_action = this_rfid_last_exit

                        check_time = int(this_rfid_last_attendance_action + attendance_not_allowed_timeout)

                        print('rfid_read_time: ' + str(rfid_read_time))
                        print('this_rfid_last_attendance_action: ' + str(this_rfid_last_attendance_action))
                        print('check_time: ' + str(check_time))

                        if rfid_read_time < check_time:  # attendance_not_allowed_timeout has NOT passed. NOT ready to apply user log.
                            our_result['status'] = 32
                            # flash('attendance_not_allowed_timeout has NOT passed.')
                            # print('STATUS 32 - NOT allowed to apply user log.')
                            publish('fingerPrintStatus', our_result)

                        elif rfid_read_time >= check_time:  # attendance_not_allowed_timeout has passed. Ready to apply user log.
                            our_result['first_name'] = the_first_name
                            our_result['last_name'] = the_last_name

                            user_id_existence_clause = db.table('user_logs').where('user_id', user_related_with_this_rfid_card).order_by('id', 'desc').pluck('id')

                            # The user_logs table does NOT have this user_id, inserting the first record of this user_id
                            if user_id_existence_clause is None:
                                the_entered_at = datetime.now()  # time right now
                                db.table('user_logs').insert(user_id=user_related_with_this_rfid_card, template_position=unique_id,
                                                             entered_at=the_entered_at, hash=None,
                                                             accuracy=None)

                                our_result['status'] = 31
                                our_result['message'] = 'Successful log for this RFID card inserted in the database.'
                                our_result['last_action'] = 'None'  # The user has forgotten to attend exit on his or her last attendance or it's the first record
                                publish('fingerPrintStatus', our_result)
                                sleep(5)

                            # The user_logs table has this user_id
                            if user_id_existence_clause is not None:
                                # Retrieve the exited_at associated with the template_position from the fingers table
                                the_exited_at = db.table('user_logs').where('user_id', user_related_with_this_rfid_card).order_by('id','desc').pluck('exited_at')

                                # exited_at field is NOT empty
                                if the_exited_at is not None:
                                    # flash('exited_at field is NOT empty!')
                                    # flash('Inserting NEW record.')
                                    # time.sleep(3)
                                    the_entered_at = datetime.now()  # time right now

                                    the_very_last_exited_at = db.table('user_logs').where('user_id', user_related_with_this_rfid_card).order_by(
                                        'id',
                                        'desc').pluck(
                                        'exited_at')

                                    our_result['last_action'] = str(the_very_last_exited_at)

                                    db.table('user_logs').insert(user_id=user_related_with_this_rfid_card,
                                                                 template_position=unique_id,
                                                                 entered_at=the_entered_at, hash=None,
                                                                 accuracy=None)

                                    our_result['status'] = 35
                                    # flash('Successful log for this RFID card inserted in the database.')

                                    publish('fingerPrintStatus', our_result)
                                    sleep(5)

                                # exited_at field is empty
                                elif the_exited_at is None:
                                    # flash('exited_at field is empty!')

                                    # Retrieve the entered_at associated with the template_position from the fingers table
                                    the_very_last_entered_at = db.table('user_logs').where('user_id', user_related_with_this_rfid_card).order_by(
                                        'id',
                                        'desc').pluck(
                                        'entered_at')

                                    temp_time = the_very_last_entered_at + timedelta(
                                        seconds=working_hours)
                                    # flash('temp_time: ' + str(temp_time))
                                    the_new_entered_at = datetime.now()  # time right now

                                    # More than specified time spent from this finger scan
                                    if the_new_entered_at > temp_time:
                                        # flash('More than 60 seconds spent from this finger scan!')
                                        # flash('It is a NEW ENTER!')

                                        our_result['last_action'] = 'None'  # The user has forgotten to attend exit on his or her last attendance or it's the first record

                                        db.table('user_logs').insert(user_id=user_related_with_this_rfid_card,
                                                                     template_position=unique_id,
                                                                     entered_at=the_new_entered_at, hash=None,
                                                                     accuracy=None)

                                        our_result['status'] = 36
                                        # flash('Successful log for this RFID card inserted in the database.')

                                        publish('fingerPrintStatus', our_result)
                                        sleep(5)

                                    # Less than specified times spent from this finger scan
                                    else:
                                        # flash('Less than 60 seconds spent from this finger scan!')
                                        # flash('It is an EXIT!')
                                        # time.sleep(3)
                                        the_exited_at = datetime.now()  # time right now

                                        db.table('user_logs').where('entered_at', the_very_last_entered_at).update(
                                            exited_at=the_exited_at)

                                        our_result['last_action'] = str(the_very_last_entered_at)

                                        our_result['status'] = 37
                                        # flash('Successful log for this RFID card inserted in the database.')

                                        publish('fingerPrintStatus', our_result)
                                        sleep(5)


                else: # This RFID card is NOT registered in the rfid_cards table.
                    our_result['status'] = 33
                    # flash('This RFID card is not registered.')
                    publish('fingerPrintStatus', our_result)


        except KeyboardInterrupt:
            print(' * Terminating... ')
            os.system('kill -9 %d' % os.getpid())

        except Exception as e:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)
            print(message)

        finally:
            GPIO.cleanup()
            spi.closeSPI()

                # current_time = int(time())
                # current_time_str = str(current_time)

                # close_spi_clause = current_time_str[-2:]
                #
                # if close_spi_clause == '00':
                #     spi.closeSPI()

    else:
        sleep(1)