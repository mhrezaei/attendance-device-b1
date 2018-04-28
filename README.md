# Flask and SocketIO integration

Compatible with Python2.7

```
    > pip install -r requirements.txt
    > ./run.py

    app > config.py > app:
        app.publish to publish events from child processes

    app > routes.py:
        define static routes

    app > realtime.py:
        do non blocking algorithms here.

    app > socketio.py
        define socketio events here

    app > subscribe.py
        define publish routines here


```