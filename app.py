import random
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room    

app = Flask(__name__)
socketio = SocketIO(app)

# 存储连接的用户
connected_users = {}
opponent_map = {}

ready_users = set()

timer_thread = None
progress = {}
gameover = False
problems = []

@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('set_id')
def handle_set_id(data):
    user_id = data['id']
    # 将用户 ID 存储到字典中，限制最多两个用户
    if len(connected_users) >= 2:
        emit('id_rejected', {'id': user_id})
        return
    join_room('game', sid=request.sid)
    progress[user_id] = 0
    connected_users[user_id] = {'socket_id': request.sid}
    if len(connected_users) == 2:
        user1 = list(connected_users.keys())[0]
        user2 = list(connected_users.keys())[1]
        opponent_map[user1] = user2
        opponent_map[user2] = user1
    emit('id_accepted', {'id': user_id}, broadcast=True)
    
    
@socketio.on('disconnect')
def handle_disconnect():
    user = None
    for key, value in connected_users.items():
        if value['socket_id'] == request.sid:
            user = key
    connected_users.pop(user)
    opponent_map.clear()
    ready_users.clear()
    print(f'{user} disconnected')


@socketio.on('key_press')
def handle_key_press(data):
    # 广播按键事件给所有连接的客户端
    socketio.emit('key_event', data)


@socketio.on('ready')
def ready(data):
    user = data['id']
    ready_users.add(user)
    if len(ready_users) == 2:
        reset()
        
        game()


@socketio.on('answer')
def handle_answer(data):
    user = data['id']
    answer = data['answer']
    if problems[progress[user]]['answer'] == int(answer):
        progress[user] += 1
        if progress[user] == 10:
            socketio.emit('win', {'id': user}, room='game')
            global gameover
            gameover = True
        else:
            socketio.emit('problem', {'formula': problems[progress[user]]['formula']}, to=request.sid)
    else:
        socketio.emit('wrong', to=request.sid)
    socketio.emit('update_progress', progress, room='game')
    


def game():
    gen_problems()
    socketio.emit('problem', {'formula': problems[0]['formula']}, room='game')
    timer_thread = socketio.start_background_task(count_down)
    

def gen_problems():
    for i in range(10):
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        problem = {
            'formula': f'{num1} + {num2} =',
            'answer': num1 + num2
        }
        problems.append(problem)


def count_down():
    for i in range(30, -1, -1):
        if gameover:
            return
        socketio.emit('count_down', {'count': i}, room='game')
        socketio.sleep(1)
    socketio.emit('win', {'id': 'nobody'}, room='game')


def reset():
    global progress
    for user in ready_users:
        progress[user] = 0
    problems.clear()
    global gameover
    gameover = False

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=35000)
