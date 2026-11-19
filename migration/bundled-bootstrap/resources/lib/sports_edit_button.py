"""The Edit capsule at the top of every Sports page (approved board B): "Edit" in blue; white with "Edit · 2" while a league filter
is on. One helper for the hub, Upcoming and Leagues, so the three agree. Uses the existing pill texture and text styles."""
import status_ui as u

ID = 9007
W, H = 250, 78


def xml(p, x, y):
    P = u.P
    off = p.image(0, 0, W, H, p.MEDIA + 'pill_72.png', '2A0A84FF', '<visible>String.IsEmpty(Window().Property(edit.on))</visible>', border=39)
    on = p.image(0, 0, W, H, p.MEDIA + 'pill_72.png', p.WHITE, '<visible>!String.IsEmpty(Window().Property(edit.on))</visible>', border=39)
    label = (u.text(p, 0, 0, W, H, P('edit.label'), 'p_foot_b', p.ACCENT, 'center')
             .replace('</control>', '<visible>String.IsEmpty(Window().Property(edit.on))</visible></control>', 1)
             + u.text(p, 0, 0, W, H, P('edit.label'), 'p_foot_b', 'FF000000', 'center')
             .replace('</control>', '<visible>!String.IsEmpty(Window().Property(edit.on))</visible></control>', 1))
    tap = ('<control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>118</height><label></label>'
           '<texturefocus /><texturenofocus /><animation effect="fade" start="100" end="65" time="0" condition="Control.HasFocus(%d)">Conditional</animation></control>'
           % (ID, W, ID))
    return '<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>%s%s%s%s</control>' % (x, y, W, H, off, on, label, tap)
