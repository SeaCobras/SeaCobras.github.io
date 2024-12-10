from textx import metamodel_from_file
from audio import analyze_for_mix

GRAMMAR_FILE = 'dj.tx'
DSL_MODEL_FILE = 'mix.dj'


def camelot_key_order(key):
    """
    Returns the Camelot wheel order for a given key.
    Example: "1A" -> 1, "12B" -> 24.
    """
    try:
        if key[-1] == "A":
            return int(key[:-1])
        elif key[-1] == "B":
            return int(key[:-1]) + 12
    except ValueError:
        return float("inf")  # Invalid key gets sorted to the end


def organize_songs(songs, identifier):
    """
    Organizes songs based on the provided identifier.
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
    Organizes all songs based on the identifier and prints the results.
    """
    songs = [cmd for cmd in commands if cmd.__class__.__name__ == "Song"]
    organized_songs = organize_songs(songs, identifier)

    print(f"All songs organized by {identifier}:")
    for song in organized_songs:
        if identifier in {"song name", "artist"}:
            print(f"{song.name} by {song.artist}")
        elif identifier == "bpm":
            print(f"{song.name} (BPM: {song.bpm})")
        elif identifier == "key":
            print(f"{song.name} (Key: {song.key})")


def handle_organize_genre(commands, genre, identifier):
    """
    Organizes songs of a specific genre based on the identifier and prints the results.
    """
    songs = [cmd for cmd in commands if cmd.__class__.__name__ == "Song" and cmd.genre.lower() == genre.lower()]
    organized_songs = organize_songs(songs, identifier)

    print(f"{genre} songs organized by {identifier}:")
    for song in organized_songs:
        if identifier in {"song name", "artist"}:
            print(f"{song.name} by {song.artist}")
        elif identifier == "bpm":
            print(f"{song.name} (BPM: {song.bpm})")
        elif identifier == "key":
            print(f"{song.name} (Key: {song.key})")


def search(song_name, commands):
    """
    Searches for a song by name and prints its details.
    """
    songs = [cmd for cmd in commands if cmd.__class__.__name__ == "Song"]
    for song in songs:
        if song.name.lower() == song_name.lower():
            return (
                f"Song: {song.name}\n"
                f"  Artist: {song.artist}\n"
                f"  BPM: {song.bpm}\n"
                f"  Key: {song.key}\n"
                f"  Genre: {song.genre}"
            )
    return f"Error: Song '{song_name}' not found in the database."


def handle_audio_analysis(input_file, bpm, bars=8):
    """
    Analyzes an audio file and prints suggested mix points.
    """
    try:
        print(f"Analyzing audio: {input_file}")
        mix_data = analyze_for_mix(input_file, bpm, bars)
        print("Analysis Complete:", mix_data)
    except Exception as e:
        print(f"Error analyzing audio: {e}")


def scratch_song(song_name, commands):
    """
    Removes a song by its name from the list of commands.
    """
    songs = [cmd for cmd in commands if cmd.__class__.__name__ == "Song"]
    for song in songs:
        if song.name.lower() == song_name.lower():
            commands.remove(song)
            print(f"Song '{song.name}' by {song.artist} has been scratched.")
            return
    print(f"Error: Song '{song_name}' not found in the database.")


def main():
    """
    Main entry point for processing the DJ language file.
    """
    dj_metamodel = metamodel_from_file(GRAMMAR_FILE)

    try:
        dj_program = dj_metamodel.model_from_file(DSL_MODEL_FILE)
    except Exception as e:
        print(f"Error parsing the DSL file: {e}")
        return

    print("Processing program:")
    for command in dj_program.commands:
        if command.__class__.__name__ == "Song":
            print(f"Added song: {command.name} by {command.artist} ({command.genre})")
        elif command.__class__.__name__ == "SearchCommand":
            print(f"\nExecuting search for: {command.name}")
            result = search(command.name, dj_program.commands)
            print(result)
        elif command.__class__.__name__ == "AnalyzeCommand":
            bars = getattr(command, 'bars', 8)
            handle_audio_analysis(command.file_path, command.bpm, bars)
        elif command.__class__.__name__ == "OrganizeAllCommand":
            handle_organize_all(dj_program.commands, command.identifier)
        elif command.__class__.__name__ == "OrganizeGenreCommand":
            handle_organize_genre(dj_program.commands, command.genre, command.identifier)
        elif command.__class__.__name__ == "ScratchCommand":
            scratch_song(command.name, dj_program.commands)


if __name__ == "__main__":
    main()
