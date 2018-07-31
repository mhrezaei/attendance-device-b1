global settings_timeout
global enroll_finger_timeout
global working_hours
global enroll_rfid_timeout
global attendance_not_allowed_timeout

global handle_the_is_synced_field_period
global request_to_refresh_for_crud_on_laravel_period
global sync_users_period

global maximum_allowed_fingers_for_usual_users
global maximum_allowed_fingers_for_admin_users

settings_timeout = 15  # 15 seconds
enroll_finger_timeout = 5  # 5 seconds
enroll_rfid_timeout = 5  # 5 seconds
working_hours = 39600  # 11 hours
attendance_not_allowed_timeout = 120  # 2 minutes

handle_the_is_synced_field_period = 60  # 1 minute
request_to_refresh_for_crud_on_laravel_period = 300  # 5 minutes
sync_users_period = 900  # 15 minutes

maximum_allowed_fingers_for_usual_users = 3
maximum_allowed_fingers_for_admin_users = 5
