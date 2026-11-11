"""Video controls › speed: play slower or faster (Kodi keeps the pitch). Roadmap B.7/2.12 (owner, build 232
screenshot): the list opens in the track menu's style under the speed button, not Kodi's select box."""


def run():
    import tracks
    tracks.run('speed')


if __name__ == '__main__':
    run()
