# LyricFetch
LyricFetch is a program written in python to scrape lyrics from the internet.

It currently has two main operating modes: On demand song searching and mp3 file
tagging.

## Supported sources
Right now, LyricFetch support scraping the following websites:

* lyrics.wikia.com    
* metrolyrics.com     
* azlyrics.com        
* lyrics.com          
* darklyrics.com      
* genius.com          
* vagalume.com.br     
* musixmatch.com      
* songlyrics.com
* lyricsmode.com      
* metal-archives.com
* letras.mus.br     
* musica.com        

## File support
Right now, only MP3 files are supported. Support for other types of audio files
may come in the future, but it's not yet planned.

## Usage
### Lyrics on demand
To get LyricFetch to find the lyrics of a song by title, use the `-n` flag, and
then pass the title and artist of the song as a single argument. Make sure to
add quotes around this parameter to avoid it being split into multiple ones.

```
python lyrics.py -n 'Metallica - Master of puppets'
```

Be sure to use this specific format or the program won't be able to parse the
argument. That is, specify the artist and title in this order, and separate both
parts with a dash (case doesn't matter). This is the only format supported right
now.

### MP3 tagging
If you give the program a file or set of files as a parameter, LyricFetch will
read the metadata of those files and search for lyrics on the internet for them.
When found, the program will automatically store the lyrics as additional (ID3
v2.3 'lyrics' tag) metadata for those files.

```
python lyrics.py a_very_cool_song.mp3 a_sad_song.mp3 that_other_song_i_dont_know.mp3
```

If you prefer, you can use the `-r` flag, and LyricFetch will scan the specified
folder (or the current one if no extra parameter is given) for MP3s, and find
lyrics for every one of them.

```
python lyrics.py -r
```

If you have a very large set of MP3s (welcome to the club), you can speed up the
execution by using the `-j` flag and the number of parallel processes you want
to use. In a modern computer with 8-cores, this is a very typical configuration
to launch this program:

```
python lyrics.py -j8 -r
```

Refer to the `-h` flag for info on more options.

## Contributing
If you want to contribute to this project you are more than welcome to do so. As
usual, fork this repo and publish a Pull Request on github so we can discuss
the implementation details like civilized people.
