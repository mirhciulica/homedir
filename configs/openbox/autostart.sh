#!/bin/sh

#. $GLOBALAUTOSTART

sflock &
conky -d &
tint2 &
numlockx &
parcellite &
thunar --daemon &
pidgin &
kupfer &
python2 ~/bin/desktopd > ~/temp/desktopd & #/dev/null &
pulseaudio --start &
(amixer -c 0 sset 'Input Source' 'Ext Mic') &
setxkbmap ro &
#dropboxd &
#nvidia-settings --load-config-only &
