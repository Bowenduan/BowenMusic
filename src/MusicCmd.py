import copy
import json
import os
import sys
import threading
from cmd import Cmd

import mpv
from wcwidth import wcswidth

from api import (MiguMusicAPI, NeteaseCloudMusicAPI, QQMusicApi,
                 convert_interval, convert_singerlist)



class MusicShell(Cmd):
    ''' Main command shell '''

    prompt = 'BowenMusic> '
    with open('src/intro.txt', 'r') as f:
        intro = f.read()   # welcome

    def __init__(self):
        Cmd.__init__(self)

        self.search_result = {
            'source': '',
            'content': []
        }
        self.api = QQMusicApi() # default qq
        self.current_song = None # dict()
        self.playlist = list()
        # self.player = mpv.MPV(ytdl=True)

        # playing signal
        self.playing_s = False
        self.playing_pl = False
        self.interrupt = False
        self.playing = False

        # initialize playlist info
        self._get_playlist_info()


    # command #
    def do_pl(self, arg):
        ''' show playlist 
        > pl          # all playlists overview
        > pl 2    # show songs in 2nd playlist
        '''
        # check playlist exists
        self._get_playlist_info()
        if len(self.playlist) == 0:
            print('No playlist found, use `cpl` to create one.')
            return

        # no arg, show all playlists' names
        if arg == '':
            index = 1
            for index in range(len(self.playlist)):
                print('{}. {}'.format(index+1, self.playlist[index]))
            return

        try: # if arg is `int` and in range
            pl_index = int(arg)
            assert (pl_index >= 1 and pl_index <= len(self.playlist))
        except:
            print('Arguments should be in [1, {}].'.format(len(self.playlist)))
            return

        print('\n歌单: {}'.format(self.playlist[pl_index-1]))
        print('-'*15)
        print('{}{}{}{}'.format(
            self._rpad('', 4),
            self._rpad('歌曲', 30), 
            self._rpad('歌手', 20),
            self._rpad('专辑', 30)))
        print('-'*80)
        with open(os.path.join(self.LIST_DIR, 
            '{}.json'.format(self.playlist[pl_index-1])), 'r') as f:
            song_list = json.load(f)

        for index in range(len(song_list)):
            print('{}{}{}{}'.format(
                self._rpad(str(index+1)+'.', 4), 
                self._rpad(song_list[index]['song_name'], 30),
                self._rpad(song_list[index]['singers'], 20),
                self._rpad(song_list[index]['album_name'], 30)))
        print('-'*80)


    def do_cpl(self, arg):
        ''' create playlist '''
        print('Please input the name of new playlist: ', end='')
        pl_name = input()
        for file_path in os.listdir(self.LIST_DIR):
            if pl_name == file_path.split('.')[0]:
                print('Playlist {} already exists.'.format(pl_name))
                return
        # create playlist json file
        with open('{}/{}.json'.format(self.LIST_DIR, pl_name), 'w') as f:
            f.write('[]')
        print('Playlist {} created.'.format(pl_name))
        self._get_playlist_info()


    def do_rpl(self, arg):
        ''' rename playlist '''
        # check playlist exists
        if len(self.playlist) == 0:
            print('No playlist found, use `cpl` to create one.')
            return
        # arg format
        if arg == '':
            print('Not enough arguments, the index of playlist should be offered.')
            return
        try: # if arg is `int` and in range
            pl_index = int(arg)
            assert (pl_index >= 1 and pl_index <= len(self.playlist))
        except:
            print('Arguments should be in [1, {}].'.format(len(self.playlist)))
            return
        
        # check if the playlist exists
        if os.path.exists('{}/{}.json'.format(self.LIST_DIR, self.playlist[pl_index-1])):
            old_path = os.path.join(self.LIST_DIR, self.playlist[pl_index-1]+'.json')   
        else:
            print('Playlist {} doesn\'t exist.'.format(self.playlist[pl_index-1]))
            return

        # get new name from user
        print('Please input a new name: ', end='')
        pl_name = input()
        
        # check if new name is the same as the old name
        if pl_name == self.playlist[pl_index-1]:
            print('Name not changed.')
            return

        new_path = os.path.join(self.LIST_DIR, pl_name+'.json')
        os.rename(old_path, new_path)
        print('Playlist {} is renamed to {}.'.format(self.playlist[pl_index-1], pl_name))
        self._get_playlist_info()


    def do_dpl(self, arg):
        ''' delete playlist '''
        # check playlist exists
        if len(self.playlist) == 0:
            print('No playlist found, user `cpl` to create one.')
            return
        # arg format
        if arg == '':
            print('Not enough arguments, the index of playlist should be offered.')
            return
        try: # if arg is `int` and in range
            pl_index = int(arg)
            assert (pl_index >= 1 and pl_index <= len(self.playlist))
        except:
            print('Arguments should be in [1, {}].'.format(len(self.playlist)))
            return
        # check if the playlist exists
        if os.path.exists('{}/{}.json'.format(self.LIST_DIR, self.playlist[pl_index-1])):
            delete_path = os.path.join(self.LIST_DIR, self.playlist[pl_index-1]+'.json')
        else:
            print('Playlist {} doesn\'t exist.'.format(self.playlist[pl_index-1]))
            return
        
        os.remove(delete_path)
        print('Playlist {} is deleted.'.format(self.playlist[pl_index-1]))
        self._get_playlist_info()
        

    def do_search(self, keyword):
        ''' search according to keyword
            results are stored in `list` self.search_result
        '''
        # check arg
        if keyword == '':
            print('Not enough arguments, keywords should be offered.')
            return
        if self.api.name == 'qq':
            self.search_result['source'] = 'qq'
            self.search_result['content'] = self.api.search(1, keyword)
            if len(self.search_result['content']) != 0: # result exists
                self._show_search()
            else:
                print('No result found.')
        elif self.api.name == 'netease':
            self.search_result['source'] = 'netease'
            self.search_result['content'] = self.api.search(keyword, 1)
            if len(self.search_result['content']) != 0:
                self._show_search()
            else:
                print('No result found.')
        elif self.api.name == 'migu':
            self.search_result['source'] = 'migu'
            self.search_result['content'] = self.api.search(keyword)
            if len(self.search_result['content']) != 0:
                self._show_search()
            else:
                print('No result found.')
        else:
            print('api name not found.')
            return


    def do_add(self, arg):
        ''' add songs in last search result to playlist 
        > add 10 1 # 10 is index in search result, 1 is index of playlist
        '''
        # check search result
        if len(self.search_result['content']) == 0:
            print('No search result, do search first.')
            return
        
        # check playlist exists
        if len(self.playlist) == 0:
            print('No playlist found, use `cpl` to create one.')
            return

        # check arguments format
        arg_list = arg.split() # check number of arguments        
        if len(arg_list) < 2:
            print('Not enough arguments, the number of arguments should be 2.')
            return
        elif len(arg_list) > 2:
            print('Too much arguments, the number of arguments should be 2.')
            return
        try: # check if arguments are number
            s_index = int(arg_list[0])  # index in search result
            pl_index = int(arg_list[1]) # index in playlist
        except:
            print('Arguments should be [the index in search result] [the index of playlist].')
            return
        
        # check if index is out of range
        s_index_upper_limit = len(self.search_result['content']) if len(self.search_result['content']) <= 10 else 10
        if s_index < 1 or s_index > s_index_upper_limit:
            print('The index in search result must be in [1, {}].'.format(s_index_upper_limit))
            return
        if pl_index < 1 or pl_index > len(self.playlist):
            print('The index of playlist must be in [1, {}].'.format(len(self.playlist)))
            return

        # add song to playlist
        add_song = self.search_result['content'][s_index-1]
        source = self.search_result['source']
        pl_name = self.playlist[pl_index-1]

        # if playlist name exists locally
        if os.path.exists('{}/{}.json'.format(self.LIST_DIR, pl_name)):
            full_path = '{}/{}.json'.format(self.LIST_DIR, pl_name)
        else:
            print('playlist {} dosen\'t exist.'.format(pl_name))
            return

        # generate stored info
        music_info = dict()
        music_info['source'] = source
        music_info['song_name'] = add_song['song_name']
        music_info['singers'] = add_song['singer_list'] if source == 'migu' else convert_singerlist(add_song['singer_list'])
        music_info['album_name'] = add_song['album_name']
        music_info['interval'] = '' if source == 'migu' else convert_interval(add_song['interval'])
        music_info['song_mid'] = add_song['song_mid']
        music_info['url'] = add_song['url'] if source == 'migu' else ''

        # add to playlist
        with open(full_path, 'r') as f:
            song_list = json.load(f)
        song_list.append(music_info)
        with open(full_path, 'w') as f:
            json.dump(song_list, f, indent=1)

        print('Add {} to playlist {} successfully.'.format(add_song['song_name'], pl_name))


    def do_play(self, arg):
        ''' play songs 
        > play        # default play from playlist 1
        > play -pl 2  # play from playlist 2
        > play -s 2   # play the 2nd song in the last search result
        '''
        # update playlist
        self._get_playlist_info()

        # play from playlist 1 by default
        if arg == '':
            if len(self.playlist) == 0:
                print('No playlist found, use `cpl` to create one.')
                return
            pl_name = self.playlist[0]
            pl_path = os.path.join(self.LIST_DIR, pl_name+'.json')
            with open(pl_path, 'r') as f:
                song_list = json.load(f)
            if len(song_list) == 0:
                print('No song found in playlist {}.'.format(pl_name))
                return
            
            play_pl_thread = threading.Thread(target=self._play_from_playlist, args=(song_list,))
            play_pl_thread.start()

        # play from playlist or search
        else:
            # args number
            args = arg.split()
            if len(args) < 2:
                print('Not enough arguments, use `help play` for more information.')
                return
            if len(args) > 2:
                print('Too much arguments, use `help play` for more information.')
                return

            # check mode
            mode = args[0]
            if mode not in ['-pl', '-s']:
                print('Arguments error, use `help play` for more information.')
                return

            # play from playlist
            if mode == '-pl':
                if len(self.playlist) == 0:
                    print('No playlist found, use `cpl` to create one.')
                    return
                try:
                    pl_index = int(args[1])
                    assert pl_index >= 1 and pl_index <= len(self.playlist)
                except:
                    print('playlist index should be in [1, {}].'.format(len(self.playlist)))
                    return
                pl_name = self.playlist[pl_index-1]
                pl_path = os.path.join(self.LIST_DIR, pl_name+'.json')
                with open(pl_path, 'r') as f:
                    song_list = json.load(f)
                if len(song_list) == 0:
                    print('No song found in playlist {}.'.format(pl_name))
                    return
                
                play_pl_thread = threading.Thread(
                    target=self._play_from_playlist, 
                    args=(song_list,))

                play_pl_thread.start()
            
            # play from search result
            elif mode == '-s':
                if len(self.search_result['content']) == 0:
                    print('No search result, do search first.')
                    return

                s_index_upper_limit = len(self.search_result['content']) if len(self.search_result['content']) <= 10 else 10
                try:
                    s_index = int(args[1])
                    assert s_index >= 1 and s_index <= s_index_upper_limit
                except:
                    print('The index in search result must be in [1, {}].'.format(s_index_upper_limit))
                
                # song info
                play_song = copy.deepcopy(self.search_result['content'][s_index-1])
                play_song['source'] = self.search_result['source']
                play_song['singers'] = play_song['singer_list'] if play_song['source'] == 'migu' else convert_singerlist(play_song['singer_list'])
                play_song['interval'] = '' if play_song['source'] == 'migu' else convert_interval(play_song['interval'])

                play_s_thread = threading.Thread(target=self._play_from_search, args=(play_song,))
                play_s_thread.start()


    def do_m(self, arg):
        ''' pause or continue the player '''
        try:
            if self.player._get_property('pause') == False:
                self.player._set_property('pause', True)
                print('pause.')
            else:
                self.player._set_property('pause', False)
                print('continue')
        except:
            print('No song is being played, use `play` first.')
    

    def _play_from_search(self, song):
        # song url
        if song['source'] == 'migu':
            url = song['url']
        elif song['source'] == 'qq':
            url = QQMusicApi().get_url(song['song_mid'])
        elif song['source'] == 'netease':
            url = NeteaseCloudMusicAPI().get_url(song['song_mid'])

        # check url
        if url == '':
            print('You need {} vip to listen {}.'.format(
                self.search_result['source'],
                play_song['song_name']))
            return

        # player is occupied by playing pl
        if self.playing == True:
            self.interrupt = True
            self.player.terminate()
        self.playing = True

        self.player = mpv.MPV(ytdl=True)
        self.event_s = threading.Event()
        play_thread = threading.Thread(target=self.__play_search_base, args=(url,))
        play_thread.start()
        self.current_song = song
        self.event_s.wait()

        if self.interrupt == True:
            self.interrupt = False
            return

        self.playing = False
        self.player.terminate()
        

    def __play_search_base(self, url):
        self.player.play(url)
        self.player.wait_for_playback()
        self.current_song = None
        self.event_s.set()


    def _play_from_playlist(self, song_list):
        if self.playing == True:
            self.interrupt = True
            self.player.terminate()
        
        self.playing = True
        self.player = mpv.MPV(ytdl=True)
        
        for song in song_list:
            if song['source'] == 'migu':
                url = song['url']
            elif song['source'] == 'qq':
                url = QQMusicApi().get_url(song['song_mid'])
            elif song['source'] == 'netease':
                url = NeteaseCloudMusicAPI().get_url(song['song_mid'])
            if url == '':
                print('You need {} vip to listen {}.'.format(
                    song['source'], 
                    song['song_name']))
                continue
            
            self.event_pl = threading.Event()
            play_thread = threading.Thread(target=self.__play_pl_base, args=(url,))
            play_thread.start()
            self.current_song = song
            self.event_pl.wait()

            # interrupt by playing search
            if self.interrupt == True:
                self.interrupt = False
                return
        
        self.playing = False
        self.player.terminate()

    def __play_pl_base(self, url):
        self.player.play(url)
        # self.player.wait_for_playback()
        self.player.wait_for_shutdown()
        self.current_song = None
        self.event_pl.set()


    def do_i(self, arg):
        ''' print current playing song's info '''
        if self.current_song == None:
            print('No song is playing.')
            return
        # print(self.current_song)
        try:
            # print(self.player._get_property('time-pos'))
            if self.current_song['source'] == 'migu':
                total_time = ''
            else:
                total_time = '/' + self.current_song['interval']


            print('Playing {} - {}  {}{}'.format(
                self.current_song['song_name'], 
                self.current_song['singers'],
                convert_interval(int(self.player._get_property('time-pos'))),
                total_time))
        except:
            print('No song is playing.')


    def do_cs(self, arg):
        ''' change search source
        arg must be in 'qq', 'netease', 'migu'
        '''
        if arg == '':
            # stay current api
            return
        if arg == 'qq':
            self.api = QQMusicApi()
            print('Source is changed to qq music.')
        elif arg == 'netease':
            self.api = NeteaseCloudMusicAPI()
            print('Source is changed to netease cloud music.')
        elif arg == 'migu':
            self.api = MiguMusicAPI()
            print('Source is changed to migu music.')
        else:
            print('Music source must be in qq, netease or migu.')


    def do_s(self, arg):
        ''' print current music source '''
        print('Current source is \'{}\''.format(self.api.name))


    def do_quit(self, arg):
        print('Wish you good luck.')
        return True
    def do_bye(self, arg):
        return self.do_quit(arg)
    def do_exit(self, arg):
        return self.do_quit(arg)
    def default(self, arg):
        print('Command not defined, use help for more information.')


    def _get_playlist_info(self):
        self.LIST_DIR = 'userdata/playlist'
        self.playlist.clear()
        for file_path in os.listdir(self.LIST_DIR):
            playlist_name = file_path.split('.')[0]
            self.playlist.append(playlist_name)

    def _show_search(self):
        ''' show first 10 search result from `list` self.search_result '''
        print('{}{}{}{}{}'.format(
            self._rpad('', 4),
            self._rpad('歌曲', 30), 
            self._rpad('歌手', 20), 
            self._rpad('专辑', 30), 
            self._rpad('时长', 10)))
        print('-'*100)
        index = 1
        for result in self.search_result['content']:
            if self.search_result['source'] != 'migu':
                singers = convert_singerlist(result['singer_list'])
            else:
                singers = result['singer_list']
            print('{}{}{}{}{}'.format(
                self._rpad(str(index)+'.', 4),
                self._rpad(result['song_name'], 30), 
                self._rpad(singers, 20),
                self._rpad(result['album_name'], 30), 
                self._rpad(convert_interval(result['interval']), 10)))
            index += 1
            if index == 11: # show only ten results
                break
        print('-'*100)

    def _lpad(self, text, length, padding=' '):
        ''' left pad for printing, not used '''
        return padding * max(0, (length-wcswidth(text))) + text

    def _rpad(self, text, length, padding=' '):
        ''' right pad for printing 
        if len(text) is larger than length, shorten the text
        '''
        while length - wcswidth(text) <= 0:
            text = text[0: len(text)-1]
        return text + padding * max(0, (length-wcswidth(text)))



if __name__ == '__main__':
    MusicShell().cmdloop()
