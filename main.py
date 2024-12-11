from textx import metamodel_from_file
from audio import bestMix_for_audio, detect_bpm
import os

GRAMMAR_FILE = 'dj.tx'
DSL_MODEL_FILE = 'mix.dj'

def camelot_key_order(key):

    try:
        if key[-1] == "A":
            return int(key[:-1])
        elif key[-1] == "B":
            return int(key[:-1]) + 12
    except ValueError:
        return float("inf")  

def organize_songs(songs, identifier):
    """
    Organizes due to identifier
    """
    if identifier == "bpm":
        return sorted(songs, key=lambda song: song.bpm)
    elif identifier == "song name":
        return sorted(songs, key=lambda song: song.name.lower(), reverse=True)
    elif identifier == "artist":
        return sorted(songs, key=lambda song: song.artist.lower(), reverse=True)
    elif identifier == "key":
        return sorted(songs, key=lambda song: camelot_key_order(song.key))
    else:
        raise ValueError(f"Invalid identifier: {identifier}")

def handle_organize_all(commands, identifier):
    """
    Organizes all songs based on the identifier
    """
    songs = [cmd for cmd in commands if cmd.__class__.__name__ == "Song"]
    organized_songs = organize_songs(songs, identifier)

    print("\n")
    print(f"All songs organized by {identifier}:")
    for song in organized_songs:
        if identifier in {"song name", "artist"}:
            print(f"{song.name} by {song.artist}")
        elif identifier == "bpm":
            print(f"{song.name} (BPM: {song.bpm})")
        elif identifier == "key":
            print(f"{song.name} (Key: {song.key})")
    print("\n")

def handle_variable_declaration(declaration, variables):
    """
    Variable declaration
    """
    name = declaration.name
    value = evaluate_expression(declaration.value, variables)
    variables[name] = value
    print(f"Variable '{name}' set to {value}.")

def search(song_name, commands, scratched_songs):
    """
    Searches for a song by name and prints all info
    """
    if song_name.lower() in scratched_songs:
        return f"Error: Song '{song_name}' has been scratched and cannot be found."

    songs = [cmd for cmd in commands if cmd.__class__.__name__ == "Song"]
    for song in songs:
        if song.name.lower() == song_name.lower():
            return (
                f"  Song: {song.name}\n"
                f"  Artist: {song.artist}\n"
                f"  BPM: {song.bpm}\n"
                f"  Key: {song.key}\n"
                f"  Genre: {song.category}"
            )
    return f"Error: Song '{song_name}' not found in the database."

def handle_audio_analysis(input_ref, bpm=None, bars=8, commands=None):
    """
    Analyzes audio
    """
    try:
        if commands:
            songs = [cmd for cmd in commands if cmd.__class__.__name__ == "Song"]
            for song in songs:
                if song.name.lower() == input_ref.lower():
                    input_ref = song.audio_file
                    bpm = bpm or song.bpm
                    break
        else:
            raise ValueError(f"Song '{input_ref}' not found in the database.")

        if bpm is None:
            print(f"Calculating BPM for: {input_ref}")
            bpm = detect_bpm(input_ref)

        print(f"Analyzing audio: {input_ref}")
        mix_data = bestMix_for_audio(input_ref, bpm, bars)
        print("Analysis Complete:", mix_data)
    except Exception as e:
        print(f"Error analyzing audio: {e}")

def scratch_song(song_name, commands, scratched_songs):
    """
    Removes a song by its name 
    """
    for song in list(commands):  
        if song.__class__.__name__ == "Song" and song.name.lower() == song_name.lower():
            commands.remove(song)
            scratched_songs.add(song_name.lower())  
            print(f"Song '{song.name}' by {song.artist} has been scratched.")
            return
    print(f"Error: Song '{song_name}' not found in the database.") 

def add_audio_file(song_name, file_path, commands):
    """
    Attaches an MP3 file to a song
    """
    songs = [cmd for cmd in commands if cmd.__class__.__name__ == "Song"]
    for song in songs:
        if song.name.lower() == song_name.lower():
            song.audio_file = file_path
            print(f"Audio file '{file_path}' successfully attached to song '{song.name}'.")
            return
    print(f"Error: Song '{song_name}' not found in the database.")

def initialize_song(song):
    """
    Initialize a Song object 
    """
    print(f"Initializing song with name='{song.name}', artist='{song.artist}', category='{song.category}', file='{song.file}'")
    song.audio_file = song.file
    if not os.path.exists(song.audio_file):
        raise ValueError(f"Audio file '{song.audio_file}' does not exist for song '{song.name}'.")

    song.bpm = detect_bpm(song.audio_file)
    song.key = "Unknown"
    
def handle_shout_command(command, context):
    """
    Print statement
    """
    try:
        value = evaluate_expression(command.expression, context) 

        if isinstance(value, (int, float, bool)):
            value = str(value)
        elif isinstance(value, list):
            value = "".join(str(item) for item in value)
        
        print(value)
    except Exception as e:
        print(f"Error in shout command: {e}")
        
def handle_organize_genre(commands, genre, identifier):
    """
    Filters songs by genre 
    """
    
    songs_by_genre = [cmd for cmd in commands if cmd.__class__.__name__ == "Song" and cmd.category == genre]

    if not songs_by_genre:
        print(f"No songs found in genre '{genre}'.")
        return

    
    organized_songs = organize_songs(songs_by_genre, identifier)

    print(f"Songs in genre '{genre}' organized by {identifier}:")
    for song in organized_songs:
        if identifier in {"song name", "artist"}:
            print(f"{song.name} by {song.artist}")
        elif identifier == "bpm":
            print(f"{song.name} (BPM: {song.bpm})")
        elif identifier == "key":
            print(f"{song.name} (Key: {song.key})")


def execute_command(command, context, scratched_songs):
    if command.__class__.__name__ == "Song":
        print("\n")
        print(f"Added song: {command.name} by {command.artist} ({command.category})")
    elif command.__class__.__name__ == "SearchCommand":
        result = search(command.name, context['commands'], scratched_songs)
        print(result)
    elif command.__class__.__name__ == "AnalyzeCommand":
        bars = getattr(command, 'bars', 8)  
        bpm = getattr(command, 'bpm', None)  
        input_ref = getattr(command, 'song_name', None) or getattr(command, 'file_path', None)
        handle_audio_analysis(input_ref, bpm, bars, context['commands'])
    elif command.__class__.__name__ == "OrganizeAllCommand":
        handle_organize_all(context['commands'], command.identifier)
    elif command.__class__.__name__ == "OrganizeGenreCommand":
        handle_organize_genre(context['commands'], command.genre, command.identifier)
    elif command.__class__.__name__ == "ScratchCommand":
        scratch_song(command.name, context['commands'], scratched_songs)
    elif command.__class__.__name__ == "AddAudioCommand":
        print(f"Executing addAudio for song '{command.song_name}' with file '{command.file_path}'.")
        add_audio_file(command.song_name, command.file_path, context['commands'])
    elif command.__class__.__name__ == "IfStatement":
        handle_if_statement(command, context, scratched_songs)  
    elif command.__class__.__name__ == "SetCommand":
        handle_set_command(command, context)
    elif command.__class__.__name__ == "ShoutCommand":
        handle_shout_command(command, context)
    elif command.__class__.__name__ == "SpinStatement":
        handle_spin_statement(command, context, scratched_songs) 
    elif command.__class__.__name__ == "Assignment":
        handle_set_command(command, context)




def handle_set_command(command, context):
    """
    Set command
    """
    name = command.name
    value = evaluate_expression(command.expression, context)
    
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    
    context['variables'][name] = value

def handle_if_statement(command, context, scratched_songs):

    handle_set_command(command.init, context)

    condition = command.condition
    iteration = command.iteration
    commands = command.commands

    while evaluate_condition(condition, context):
        for cmd in commands:
            execute_command(cmd, context, scratched_songs)

        handle_set_command(iteration, context)
     
def handle_spin_statement(command, context, scratched_songs):
    """
    For loop
    """
    condition = command.condition
    commands = command.commands

    while evaluate_condition(condition, context):
        for cmd in commands:
            execute_command(cmd, context, scratched_songs) 


def evaluate_condition(condition, context):
    """
    Evaluates a condition 
    """
    left = evaluate_expression(condition.left, context)
    right = evaluate_expression(condition.right, context)
    operator = condition.operator

    if operator == '<':
        return left < right
    elif operator == '>':
        return left > right
    elif operator == '<=':
        return left <= right
    elif operator == '>=':
        return left >= right
    elif operator == '==':
        return left == right
    elif operator == '!=':
        return left != right
    else:
        raise ValueError(f"Unsupported operator: {operator}")


def evaluate_expression(expression, context):
    """
    Evaluates an expression
    """
    if isinstance(expression, str):
        if expression in context['variables']:
            return context['variables'][expression]
        return expression  
    elif isinstance(expression, (int, float, bool)):
        return expression
    elif hasattr(expression, 'left') and hasattr(expression, 'operator') and hasattr(expression, 'right'):
        left_value = evaluate_expression(expression.left, context)
        right_value = evaluate_expression(expression.right, context)
        operator = expression.operator

        if operator == '+':
            if isinstance(left_value, str) or isinstance(right_value, str):
                return str(left_value) + str(right_value)
            return left_value + right_value
        elif operator == '-':
            return left_value - right_value
        elif operator == '*':
            return left_value * right_value
        elif operator == '/':
            return left_value / right_value if right_value != 0 else float('inf')
        else:
            raise ValueError(f"Unsupported operator: {operator}")
    else:
        raise ValueError(f"Unknown expression type: {expression.__class__.__name__}")

def main():
    dj_metamodel = metamodel_from_file(GRAMMAR_FILE)

    dj_metamodel.register_obj_processors({
        'Song': lambda song: initialize_song(song)
    })

    try:
        with open(DSL_MODEL_FILE, 'r') as file:
            file.read()
        dj_program = dj_metamodel.model_from_file(DSL_MODEL_FILE)
    except Exception as e:
        print(f"Error parsing the DSL file: {e}")
        return

    context = {"commands": dj_program.commands, "variables": {}}
    scratched_songs = set()  

    for command in dj_program.commands:
        execute_command(command, context, scratched_songs)

if __name__ == "__main__":
    main()
