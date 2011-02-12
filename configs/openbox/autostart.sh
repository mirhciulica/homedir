#!/bin/sh

#. $GLOBALAUTOSTART

sflock &
conky -d &
tint2 &
numlockx &
parcellite &
thunar --daemon &
pidgin &
python2 ~/bin/desktopd > /dev/null &
pulseaudio --start &
(amixer -c 0 sset 'Input Source' 'Ext Mic') &
#dropboxd &
#nvidia-settings --load-config-only &
