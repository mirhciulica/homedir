#!/bin/sh

#. $GLOBALAUTOSTART

#sflock &
conky -d &
tint2 &
numlockx &
parcellite &
thunar --daemon &
nm-applet --sm-disable &
pidgin &
#kupfer &
python2 ~/bin/desktopd >> ~/temp/desktopd 2>&1 & #/dev/null &
pulseaudio --start &
(amixer -c 0 sset 'Input Source' 'Ext Mic') &
setxkbmap ro &
dropboxd &
#nvidia-settings --load-config-only &
