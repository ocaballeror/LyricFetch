"""
Collection of sample responses received from music players.

These variables are used to test the get_current_song related functions.
"""
# flake8: noqa: E501

sample_response_amarok = ('a{sv}', ([
    ('album', ('s', 'Endless Forms Most Beautiful')),
    ('albumartist', ('s', 'Nightwish')),
    ('artist', ('s', 'Nightwish')),
    ('audio-bitrate', ('i', 192)),
    ('audio-samplerate', ('i', 44100)),
    ('comment', ('s', 'Added on 28/04/2017')),
    ('genre', ('s', 'Symphonic Metal')),
    ('location', ('s', 'file:///Music/Nightwish/%5B2015%5D%20Endless%20Forms%20Most%20Beautiful/11%20The%20Greatest%20Show%20on%20Earth.mp3')),
    ('mtime', ('x', 1438000)),
    ('rating', ('i', 0)),
    ('time', ('x', 1438)),
    ('title', ('s', 'Alpenglow')),
    ('tracknumber', ('i', 11)),
    ('year', ('s', '2015'))
],))

sample_response_clementine = ('v', (
    ('a{sv}', [
        ('bitrate', ('i', 252)),
        ('mpris:artUrl', ('s', 'file:///tmp/clementine-art-y30335.jpg')),
        ('mpris:length', ('x', 1238000000)),
        ('mpris:trackid', ('s', '/org/clementineplayer/Clementine/Track/71')),
        ('xesam:album', ('s', '2112')),
        ('xesam:albumArtist', ('as', ['Rush'])),
        ('xesam:artist', ('as', ['Rush'])),
        ('xesam:autoRating', ('i', 50)),
        ('xesam:comment', ('as', ['Added on 29/09/2018'])),
        ('xesam:contentCreated', ('s', '2018-09-29T17:53:41')),
        ('xesam:discNumber', ('i', 1)),
        ('xesam:genre', ('as', ['Progressive Rock'])),
        ('xesam:lastUsed', ('s', '2018-11-11T22:11:16')),
        ('xesam:title', ('s', '2112')),
        ('xesam:trackNumber', ('i', 1)),
        ('xesam:url', ('s', 'file:///Music/Rush/[1976] 2112/01 2112.mp3')),
        ('xesam:useCount', ('i', 1)),
        ('year', ('i', 1976))
        ]
    ),))

sample_response_spotify = ('v', (
    ('a{sv}', [
        ('mpris:trackid', ('s', 'spotify:track:3Dja8y60xnXAJQLl1tX8UR')),
        ('mpris:length', ('t', 312746000)),
        ('mpris:artUrl', ('s', 'https://open.spotify.com/image/a68c1c0c6e5469a01127177933ed08cea8e81d8d')),
        ('xesam:album', ('s', 'Process Of A New Decline')),
        ('xesam:albumArtist', ('as', ['Gorod'])),
        ('xesam:artist', ('as', ['Gorod'])),
        ('xesam:autoRating', ('d', 0.14)),
        ('xesam:discNumber', ('i', 1)),
        ('xesam:title', ('s', 'Splinters Of Life')),
        ('xesam:trackNumber', ('i', 6)),
        ('xesam:url', ('s', 'https://open.spotify.com/track/3Dja8y60xnXAJQLl1tX8UR'))
        ]),
    ))

sample_response_cmus = """
status playing
file /Music/Death/[1987] Scream Bloody Gore/07 Baptized in Blood.mp3
duration 269
position 2
tag artist Death
tag album Scream Bloody Gore
tag title Baptized in Blood
tag date 1987
tag genre Death Metal
tag tracknumber 7
tag albumartist Death
tag composer Death
tag comment Added on 9/11/2017
set aaa_mode artist
set continue true
set play_library true
set play_sorted false
set replaygain track
set replaygain_limit true
set replaygain_preamp 0.000000
set repeat false
set repeat_current false
set shuffle false
set softvol false
set vol_left 0
set vol_right 0
"""
