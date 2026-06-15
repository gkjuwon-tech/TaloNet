// =============================================================================
// TaloNet "ForensIQ-1" — parametric benchtop forensic appliance
// Sealed field kiosk for post-capture media forensics on SEIZED drone storage.
//
// Units: millimetres. Coordinate frame: +X = front (operator side), +Z = up.
// Role: runs the TaloNet forensics pipeline (docs/08_사후_포렌식.md):
//   intake -> write-blocked imaging -> SHA-256 -> content/flight-log parse
//   (pymavlink/pyulog/pynmea2/dji) -> trajectory/intent -> threat-intel report,
//   then prints the report on a BUILT-IN 80 mm thermal printer and archives a
//   PDF to a write-once Evidence USB. Nothing boots the seized card; every
//   access is read-only behind a hardware WRITE-BLOCKER and chain-of-custody
//   logged. Read-only analysis of physically-secured seized media ONLY — not
//   intrusion, not jamming (the project's "Clean Defense" posture).
//
// Design note: every front-panel feature that needs an opening (screen window,
// card slots, paper exit) is a SELF-CONTAINED solid whose window is built into
// it, and is UNIONED ON TOP of the (separately cut) body. Panel cuts therefore
// never "eat" the panel features. This keeps the model 2-manifold and the face
// fully populated. Massing/packaging model, not a stress-certified part.
// Render STL:  openscad -o appliance.stl forensic_appliance.scad
// =============================================================================

/* [Case body] */
case_w           = 420;   // [280:600] external width (left<->right), mm
case_d           = 320;   // [220:480] external depth (front<->back, +X front), mm
case_h           = 220;   // [150:340] external height, mm
wall_thk         = 6;     // [3:12] enclosure wall thickness, mm
edge_cham        = 10;    // [0:24] outer rugged edge chamfer, mm
lid_h            = 34;    // [16:70] top clamshell lid band height, mm

/* [Carry handle] */
show_handle      = true;
handle_d         = 22;    // [12:36] handle bar diameter, mm
handle_rise      = 46;    // [20:90] handle clear height above lid, mm

/* [Front panel] */
panel_margin     = 18;    // [8:40] feature inset from case edges, mm
boss_proud       = 5;     // [2:12] how far front bezels stand proud of the face, mm

/* [Touchscreen] */
screen_diag_in   = 7;     // [5:12] active-area diagonal (in)
screen_16_10     = true;  // 16:10 aspect (false = 16:9)
screen_bezel     = 10;    // [4:24] bezel width around the active glass, mm

/* [Write-blocker / card intake] */
wb_block_w       = 96;    // [60:150] write-blocker module width, mm
wb_block_h       = 66;    // [40:110] write-blocker module height, mm
usd_slot_w       = 16;    // [11:24] microSD slot width, mm
usd_slot_h       = 3.0;   // [1.6:6] microSD slot height (thin), mm
sd_slot_w        = 26;    // [22:38] full-size SD slot width, mm
sd_slot_h        = 3.4;   // [2:6] full-size SD slot height (thin), mm

/* [Printer] */
printer_bay_w    = 118;   // [80:170] internal thermal-printer bay width, mm
printer_bay_h    = 96;    // [70:150] internal thermal-printer bay height, mm
paper_slot_w     = 86;    // [60:120] paper-exit slot width (80 mm roll), mm
paper_slot_h     = 5;     // [3:10] paper-exit slot height, mm
roll_od          = 70;    // [40:90] thermal paper roll outer diameter, mm

/* [Controls / LEDs] */
btn_dia          = 16;    // [10:26] pushbutton boss diameter, mm
led_dia          = 7;     // [4:12] status-LED boss diameter, mm
led_count        = 5;     // [2:10] number of status LEDs in the row
keylock_dia      = 20;    // [12:30] key-lock (tamper) cylinder diameter, mm

/* [Internals] */
show_internals   = true;  // show SBC, write-blocker PCB, printer, fan, UPS
lid_open         = 0;     // [0:160] exploded "open" lid lift, mm
sbc_board_w      = 100;   // [70:180] SBC carrier board width, mm
sbc_board_d      = 80;    // [56:140] SBC carrier board depth, mm
sbc_standoff     = 9;     // [4:20] standoff height under the SBC, mm
fan_dia          = 60;    // [30:120] cooling fan diameter, mm

/* [Rear panel] */
vent_louvres     = 6;     // [3:12] number of vent louvres

/* [Render] */
$fn              = 56;

// ----- derived ---------------------------------------------------------------
body_h     = case_h - lid_h;            // lower body band height
in_mm      = 25.4;
scr_diag   = screen_diag_in * in_mm;    // active diagonal, mm
scr_ar     = screen_16_10 ? 10/16 : 9/16;
scr_w      = scr_diag / sqrt(1 + scr_ar*scr_ar);   // active width
scr_h      = scr_w * scr_ar;                        // active height
front_x    = case_d/2;                  // outer front flat face X
eps        = 0.02;

// ----- colors ----------------------------------------------------------------
C_KHAKI   = [0.525, 0.522, 0.373];   // #86855F TaloNet signature khaki
C_DARK    = [0.08, 0.08, 0.07];
C_ALU     = [0.62, 0.62, 0.60];
C_PCB     = [0.12, 0.30, 0.16];      // green PCB
C_GLASS   = [0.05, 0.07, 0.10];      // screen glass
C_PAPER   = [0.93, 0.92, 0.86];      // thermal paper
C_LED_G   = [0.20, 0.85, 0.30];      // write-blocker "blocked = green" LED
C_LED_A   = [0.95, 0.70, 0.15];      // amber status
C_STEEL   = [0.45, 0.46, 0.48];

// =========================================================================
// FRONT-FACE FEATURE LAYOUT (Y = left<->right, Z = up)
//   LEFT  column : large 7" touchscreen, vertically centred.
//   RIGHT column : (top) WRITE-BLOCKER w/ microSD+SD slots + green LED,
//                  (mid) START/EJECT buttons + status-LED row + key-lock,
//                  (bottom) printer paper-exit + tear bar.
// =========================================================================
fp_z0 = wall_thk + panel_margin;        // bottom usable Z
fp_z1 = body_h - panel_margin;          // top usable Z

screen_zone_w = scr_w + 2*screen_bezel + 18;
right_zone_w  = max(wb_block_w, paper_slot_w + 18) + 22;
gap           = 26;
band_w        = screen_zone_w + gap + right_zone_w;
band_y0       = -band_w/2;

scr_cy = band_y0 + screen_zone_w/2;                       // screen column Y
right_cy = band_y0 + screen_zone_w + gap + right_zone_w/2;// right column Y
scr_cz = (fp_z0 + fp_z1)/2;                               // screen centred in Z

wb_cy  = right_cy;
wb_cz  = fp_z1 - wb_block_h/2 - 4;                        // write-blocker at top
clu_cy = right_cy;
clu_cz = wb_cz - wb_block_h/2 - 30;                       // control cluster mid
pr_cy  = right_cy;
pr_cz  = fp_z0 + paper_slot_h/2 + 8;                      // paper exit at bottom

// =========================================================================
// PRIMITIVES
// =========================================================================

// Rugged rounded/chamfered box: solid centred in X/Y, z in [0..h].
module rugged_box(w, d, h, cham = edge_cham) {
    c = max(cham, 0.01);
    minkowski() {
        translate([0, 0, h/2])
            cube([w - 2*c, d - 2*c, max(h - 2*c, 0.1)], center = true);
        sphere(r = c, $fn = 16);
    }
}

// A proud picture-frame bezel on the front face with a rectangular window
// punched through it (self-contained: the window is part of the solid).
// Seats 'seat' mm back into the body so it fuses to the wall (no coincident
// faces), and stands 'boss_proud' mm proud of the front plane.
module bezel_window(cy, cz, ow, oh, iw, ih, col = C_DARK, seat = 3) {
    bt = boss_proud + seat;
    bx = front_x + boss_proud/2 - seat/2;   // spans [front_x-seat, front_x+boss_proud]
    color(col)
    difference() {
        translate([bx, cy, cz]) cube([bt, ow, oh], center = true);
        translate([bx, cy, cz]) cube([bt + 1, iw, ih], center = true);
    }
}

// A short proud cylinder button/LED/lock standing off the front face (+X).
module face_stud(cy, cz, dia, col, len = 11) {
    color(col)
        translate([front_x - 1, cy, cz]) rotate([0, 90, 0])
            cylinder(h = len + 1, d = dia);
}

// =========================================================================
// CASE SHELL + LID + HANDLE
// =========================================================================
module body() {
    color(C_KHAKI)
    difference() {
        rugged_box(case_w, case_d, body_h);
        // hollow tub opening through the top
        translate([0, 0, wall_thk + body_h/2 + eps])
            cube([case_w - 2*wall_thk, case_d - 2*wall_thk, body_h], center = true);
    }
}

module lid() {
    z0 = body_h + lid_open;
    color(C_KHAKI)
    translate([0, 0, z0])
    difference() {
        rugged_box(case_w, case_d, lid_h);
        translate([0, 0, -eps])
            cube([case_w - 2*wall_thk, case_d - 2*wall_thk, (lid_h - wall_thk)*2],
                 center = true);
    }
    if (show_handle) translate([0, 0, z0 + lid_h]) carry_handle();
}

module carry_handle() {
    span = case_w * 0.5;
    r    = handle_d / 2;
    color(C_DARK) {
        for (sy = [-1, 1])
            translate([0, sy*span/2, -6]) cylinder(h = handle_rise + 6, d = handle_d);
        translate([0, 0, handle_rise]) rotate([90, 0, 0])
            cylinder(h = span + handle_d, d = handle_d, center = true);
        for (sy = [-1, 1])
            translate([0, sy*span/2, handle_rise]) sphere(r = r);
    }
}

// =========================================================================
// FRONT-WALL THROUGH-CUTS (act on the body only; openings to the cavity)
// =========================================================================
module front_wall_cuts() {
    cx = front_x - wall_thk/2;            // centred in the front wall
    ct = wall_thk + 6;                    // clean through-cut depth
    // Body holes are made LARGER than the feature apertures (clearance 'c') so
    // no face of a feature window ever coincides with a body-cut face.
    c = 3;
    // touchscreen window
    translate([cx, scr_cy, scr_cz]) cube([ct, scr_w + 2*c, scr_h + 2*c], center = true);
    // write-blocker card slots (microSD upper, SD lower)
    translate([cx, wb_cy - 10, wb_cz + 12]) cube([ct, usd_slot_w + 2*c, usd_slot_h + 2*c], center = true);
    translate([cx, wb_cy - 10, wb_cz - 6]) cube([ct, sd_slot_w + 2*c, sd_slot_h + 2*c], center = true);
    // printer paper exit
    translate([cx, pr_cy, pr_cz]) cube([ct, paper_slot_w + 2*c, paper_slot_h + 2*c], center = true);
}

// =========================================================================
// FRONT-PANEL FEATURES (self-contained; unioned on top after the cuts)
// =========================================================================
module touchscreen() {
    bezel_window(scr_cy, scr_cz, scr_w + 2*screen_bezel, scr_h + 2*screen_bezel,
                 scr_w, scr_h, C_DARK);
    // glass pane: sized to overlap the bezel ring (so it fuses there), set into
    // the larger body hole without touching its walls -> no coincident faces.
    color(C_GLASS)
        translate([front_x - 2.5, scr_cy, scr_cz]) cube([7, scr_w + 3, scr_h + 3], center = true);
}

module writeblocker_module() {
    seat = 3;
    bt = boss_proud + seat;
    bx = front_x + boss_proud/2 - seat/2;
    // raised steel block with the two card slots cut in (self-contained)
    color(C_STEEL)
    difference() {
        translate([bx, wb_cy, wb_cz]) cube([bt, wb_block_w, wb_block_h], center = true);
        translate([bx, wb_cy - 10, wb_cz + 12]) cube([bt+1, usd_slot_w, usd_slot_h], center = true);
        translate([bx, wb_cy - 10, wb_cz - 6]) cube([bt+1, sd_slot_w, sd_slot_h], center = true);
    }
    // "WRITE-BLOCKED = green" status LED on the block, beside the slots
    face_stud(wb_cy + wb_block_w/2 - 12, wb_cz + 10, led_dia, C_LED_G, len = boss_proud + 3);
}

module printer_exit() {
    seat = 3;
    bt = boss_proud + seat;
    bx = front_x + boss_proud/2 - seat/2;
    // dark surround with the paper slot punched through
    color(C_DARK)
    difference() {
        translate([bx, pr_cy, pr_cz + 2]) cube([bt, paper_slot_w + 18, paper_slot_h + 22], center = true);
        translate([bx, pr_cy, pr_cz]) cube([bt+1, paper_slot_w, paper_slot_h], center = true);
    }
    // aluminium tear bar above the slot
    color(C_ALU)
        translate([front_x + boss_proud, pr_cy, pr_cz + paper_slot_h/2 + 5])
            cube([6, paper_slot_w + 10, 3], center = true);
    // a sliver of thermal paper poking out (reaches back to the feed throat)
    color(C_PAPER)
        translate([front_x - 4, pr_cy, pr_cz]) cube([12, paper_slot_w - 4, paper_slot_h - 1.4], center = true);
}

module front_controls() {
    row1 = clu_cz + 8;     // START / EJECT buttons + key-lock
    row2 = clu_cz - 12;    // status-LED row (kept clear of the printer below)
    // START (green) + EJECT (amber) pushbuttons
    face_stud(clu_cy - 4,  row1, btn_dia, C_LED_G, len = 9);
    face_stud(clu_cy - 24, row1, btn_dia, C_LED_A, len = 9);
    // key-lock (tamper) cylinder + keyway, to the right on the same row
    face_stud(clu_cy + 26, row1, keylock_dia, C_ALU, len = 11);
    color(C_DARK)
        translate([front_x + 9, clu_cy + 26, row1])
            cube([3, 2.5, keylock_dia*0.5], center = true);
    // status-LED row
    led_pitch = led_dia + 6;
    for (i = [0 : led_count - 1])
        face_stud(clu_cy + (led_count - 1)*led_pitch/2 - i*led_pitch, row2,
                  led_dia, i % 2 == 0 ? C_LED_A : C_LED_G, len = 7);
}

module front_features() {
    touchscreen();
    writeblocker_module();
    printer_exit();
    front_controls();
}

// =========================================================================
// REAR PANEL — port surrounds (proud) with apertures cut through them + vents
// =========================================================================
function rear_py(i) = -case_w/2 + panel_margin + 30 + i*48;

module rear_ports() {
    rx = -case_d/2;
    cz = body_h * 0.55;
    // proud port surrounds (the rear_cuts punch their apertures)
    color(C_DARK)  translate([rx - 4, rear_py(0), cz]) rotate([0,90,0]) cube([28, 34, 10], center=true); // IEC power
    color(C_STEEL) translate([rx - 4, rear_py(1), cz]) rotate([0,90,0]) cube([18, 20, 10], center=true); // Ethernet
    color(C_KHAKI) translate([rx - 4, rear_py(2), cz]) rotate([0,90,0]) cube([18, 24, 10], center=true); // Evidence USB
    color(C_ALU)   translate([rx - 4, rear_py(3), cz - 34]) rotate([0,90,0]) cube([12, 9, 10], center=true); // Kensington
}

module rear_cuts() {
    rx = -case_d/2;
    cz = body_h * 0.55;
    ct = wall_thk + 14;
    translate([rx + 2, rear_py(0), cz]) rotate([0,90,0]) cube([24, 30, ct], center=true);
    translate([rx + 2, rear_py(1), cz]) rotate([0,90,0]) cube([14, 16, ct], center=true);
    translate([rx + 2, rear_py(2), cz]) rotate([0,90,0]) cube([13, 6, ct], center=true);
    translate([rx + 2, rear_py(3), cz - 34]) rotate([0,90,0]) cube([7, 3, ct], center=true);
    // vent louvres across the upper rear
    for (i = [0 : vent_louvres - 1])
        translate([rx + 2, case_w*0.20, body_h*0.30 + i*9])
            rotate([0,90,0]) cube([3.0, case_w*0.40, ct], center = true);
}

// =========================================================================
// INTERNAL SUBSYSTEM MASSING
// =========================================================================
module sbc_assembly() {
    bx = -case_d/2 + sbc_board_d/2 + wall_thk + 18;
    by = -case_w/2 + sbc_board_w/2 + wall_thk + 16;
    bz = wall_thk;
    color(C_ALU)
        for (sx = [-1, 1], sy = [-1, 1])
            translate([bx + sx*(sbc_board_d/2 - 6), by + sy*(sbc_board_w/2 - 6), bz])
                cylinder(h = sbc_standoff, d = 6);
    color(C_PCB)
        translate([bx, by, bz + sbc_standoff]) cube([sbc_board_d, sbc_board_w, 2.4], center = true);
    color(C_DARK)
        translate([bx, by, bz + sbc_standoff + 12])
            cube([sbc_board_d*0.5, sbc_board_w*0.55, 20], center = true);
}

module writeblocker_pcb() {
    bx = front_x - wall_thk - 34;
    color(C_PCB)
        translate([bx, wb_cy, wb_cz - 6]) cube([54, wb_block_w*0.8, 2.4], center = true);
    color(C_DARK)
        translate([bx + 22, wb_cy - 14, wb_cz - 6]) cube([40, 22, 14], center = true);
}

module printer_assembly() {
    bx = front_x - wall_thk - printer_bay_h/2 - 6;
    by = pr_cy;
    bz = pr_cz + printer_bay_h/2 - paper_slot_h/2 - 8;
    color(C_DARK)
        translate([bx, by, bz]) cube([printer_bay_h, printer_bay_w, printer_bay_h], center = true);
    color(C_PAPER)
        translate([bx - 6, by, bz + printer_bay_h/2 - roll_od/2 + 4]) rotate([90,0,0])
            cylinder(h = 80, d = roll_od, center = true);
    color(C_DARK)
        translate([bx - 6, by, bz + printer_bay_h/2 - roll_od/2 + 4]) rotate([90,0,0])
            cylinder(h = 82, d = roll_od*0.25, center = true);
    color(C_ALU)
        translate([(bx + front_x)/2, by, pr_cz])
            cube([abs(front_x - bx) + 4, paper_slot_w, paper_slot_h + 2], center = true);
}

module cooling_fan() {
    bx = -case_d/2 + wall_thk + 6;
    by = case_w/2 - wall_thk - fan_dia/2 - 14;
    bz = body_h/2;
    color(C_DARK)
        translate([bx, by, bz]) rotate([0, 90, 0])
            difference() {
                cube([fan_dia, fan_dia, 16], center = true);
                cylinder(h = 20, d = fan_dia - 6, center = true);
            }
    color(C_STEEL)
        translate([bx, by, bz]) rotate([0, 90, 0]) cylinder(h = 10, d = fan_dia*0.4, center = true);
}

module ups_block() {
    bw = case_w * 0.30;
    bd = case_d * 0.34;
    bh = 46;
    bx = -case_d/2 + bd/2 + wall_thk + 10;
    by = case_w/2 - bw/2 - wall_thk - 10;
    color([0.16, 0.16, 0.15])
        translate([bx, by, wall_thk + bh/2]) cube([bd, bw, bh], center = true);
    color(C_KHAKI)
        translate([bx + bd/2 - 2, by, wall_thk + bh/2]) cube([3, bw*0.7, bh*0.5], center = true);
}

module internals() {
    sbc_assembly();
    writeblocker_pcb();
    printer_assembly();
    cooling_fan();
    ups_block();
}

// =========================================================================
// ASSEMBLY
// =========================================================================
module forensiq_appliance() {
    union() {
        // body with front-wall windows + rear apertures cut (port surrounds
        // are included in the cut so their holes are punched), then ...
        difference() {
            union() {
                body();
                rear_ports();
            }
            front_wall_cuts();
            rear_cuts();
        }
        // ... self-contained front features added ON TOP (never eaten by cuts)
        front_features();
        lid();
        if (show_internals) internals();
    }
}

forensiq_appliance();
