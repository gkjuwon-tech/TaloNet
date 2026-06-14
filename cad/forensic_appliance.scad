// =============================================================================
// TaloNet "ForensIQ-1" — parametric benchtop forensic appliance
// Sealed field kiosk for post-capture media forensics on SEIZED drone storage.
//
// Units: millimetres. Coordinate frame: +X = nose/forward (operator side),
//                                        +Z = up.
// Role: runs the TaloNet forensics pipeline (docs/08_사후_포렌식.md):
//   intake -> write-blocked imaging -> SHA-256 -> content/flight-log parse
//   (pymavlink/pyulog/pynmea2/dji) -> trajectory/intent -> threat-intel report,
//   then prints the report on a BUILT-IN 80 mm thermal printer and archives a
//   PDF to a write-once Evidence USB. Nothing boots the seized card; every
//   access is read-only behind a hardware WRITE-BLOCKER and chain-of-custody
//   logged. Read-only analysis of physically-secured seized media ONLY — not
//   intrusion, not jamming (the project's "Clean Defense" posture).
//
// This is a DESIGN / packaging massing model (enclosure + panel cutouts +
// internal layout), not a stress-certified manufacturing model.
// Render STL:  openscad -o appliance.stl forensic_appliance.scad
// =============================================================================

/* [Case body] */
// Overall case external width (left<->right), mm
case_w           = 420;   // [280:600]
// Overall case external depth (front<->back, +X is front), mm
case_d           = 320;   // [220:480]
// Overall case external height, mm
case_h           = 220;   // [150:340]
// Enclosure wall thickness, mm
wall_thk         = 6;     // [3:12]
// Outer edge chamfer (rugged bevel), mm
edge_cham        = 10;    // [0:24]
// Lid height (top clamshell band), mm
lid_h            = 34;    // [16:70]

/* [Carry handle] */
// Show top carry handle massing
show_handle      = true;
// Handle bar diameter, mm
handle_d         = 22;    // [12:36]
// Handle clear height above the lid, mm
handle_rise      = 46;    // [20:90]

/* [Front panel] */
// Inset of panel features from case edges, mm
panel_margin     = 18;    // [8:40]
// Recess depth of front-panel bezels/blocks, mm
panel_recess     = 4;     // [2:10]

/* [Touchscreen] */
// Screen diagonal (in) — drives the active-area size
screen_diag_in   = 7;     // [5:12]
// 16:10 aspect (false = 16:9)
screen_16_10     = true;
// Bezel width around the active glass, mm
screen_bezel     = 9;     // [4:20]

/* [Write-blocker / card intake] */
// Write-blocker module block width, mm
wb_block_w       = 96;    // [60:150]
// Write-blocker module block height, mm
wb_block_h       = 64;    // [40:110]
// microSD slot width, mm
usd_slot_w       = 16;    // [11:24]
// microSD slot height (thin), mm
usd_slot_h       = 3.0;   // [1.6:6]
// Full-size SD slot width, mm
sd_slot_w        = 26;    // [22:38]
// Full-size SD slot height (thin), mm
sd_slot_h        = 3.4;   // [2:6]

/* [Printer] */
// Internal thermal-printer bay width, mm
printer_bay_w    = 118;   // [80:170]
// Internal thermal-printer bay height, mm
printer_bay_h    = 96;    // [70:150]
// Paper-exit slot width (80 mm roll), mm
paper_slot_w     = 86;    // [60:120]
// Paper-exit slot height, mm
paper_slot_h     = 5;     // [3:10]
// Thermal paper roll outer diameter, mm
roll_od          = 70;    // [40:90]

/* [Controls / LEDs] */
// Pushbutton boss diameter, mm
btn_dia          = 16;    // [10:26]
// Status-LED boss diameter, mm
led_dia          = 7;     // [4:12]
// Number of status LEDs in the indicator row
led_count        = 5;     // [2:10]
// Key-lock (tamper) cylinder diameter, mm
keylock_dia      = 20;    // [12:30]

/* [Internals] */
// Show internal subsystem massing (SBC, write-blocker PCB, printer, fan, UPS)
show_internals   = true;
// Lift the lid for an exploded "open" view (mm above seated)
lid_open         = 0;     // [0:160]
// SBC carrier board width (CM4 carrier / NUC-class), mm
sbc_board_w      = 100;   // [70:180]
// SBC carrier board depth, mm
sbc_board_d      = 80;    // [56:140]
// Standoff height under the SBC, mm
sbc_standoff     = 9;     // [4:20]
// Cooling fan diameter, mm
fan_dia          = 60;    // [30:120]

/* [Rear panel] */
// Number of vent louvres
vent_louvres     = 6;     // [3:12]

/* [Render] */
$fn              = 56;

// ----- derived ---------------------------------------------------------------
body_h     = case_h - lid_h;            // lower body band height
in_mm      = 25.4;
scr_diag   = screen_diag_in * in_mm;    // active diagonal, mm
scr_ar     = screen_16_10 ? 10/16 : 9/16;
scr_w      = scr_diag / sqrt(1 + scr_ar*scr_ar);   // active width
scr_h      = scr_w * scr_ar;                        // active height
front_x    = case_d/2;                  // outer front face X
eps        = 0.01;

// ----- color helpers ---------------------------------------------------------
C_KHAKI   = [0.525, 0.522, 0.373];   // #86855F TaloNet signature khaki
C_DARK    = [0.08, 0.08, 0.07];
C_ALU     = [0.62, 0.62, 0.60];
C_PCB     = [0.12, 0.30, 0.16];      // green PCB
C_GLASS   = [0.05, 0.06, 0.08];      // screen glass
C_PAPER   = [0.93, 0.92, 0.86];      // thermal paper
C_LED_G   = [0.20, 0.85, 0.30];      // write-blocker "blocked = green" LED
C_LED_A   = [0.95, 0.70, 0.15];      // amber status
C_RED     = [0.80, 0.15, 0.12];
C_STEEL   = [0.45, 0.46, 0.48];

// =========================================================================
// PRIMITIVES
// =========================================================================

// Rounded/chamfered rugged box (Minkowski of a cube with a small octahedron-
// like ball gives a rugged bevel). Returns a solid centred in X/Y, z in [0..h].
module rugged_box(w, d, h, cham = edge_cham) {
    c = max(cham, 0.01);
    minkowski() {
        // cube centred at z = h/2 so the Minkowski result spans z in [0..h]
        translate([0, 0, h/2])
            cube([w - 2*c, d - 2*c, max(h - 2*c, 0.1)], center = true);
        // low-facet sphere -> chamfer-ish rounded edges, cheap + manifold
        sphere(r = c, $fn = 16);
    }
}

// A thin labelled raised block on the front face (a recessed bezel frame).
// Drawn as a solid plate; cutouts are subtracted by the caller.
module front_plate(w, h, t = panel_recess + wall_thk) {
    translate([front_x - t/2, 0, 0])
        cube([t, w, h], center = true);   // note: w is along Y, h along Z
}

// =========================================================================
// CASE SHELL (lower body) — hollow tub, faces solid (cut later)
// Hollow body: subtract an inner box that opens through the top.
// =========================================================================
module body() {
    color(C_KHAKI)
    difference() {
        rugged_box(case_w, case_d, body_h);
        translate([0, 0, wall_thk + (body_h)/2 + eps])
            cube([case_w - 2*wall_thk, case_d - 2*wall_thk, body_h],
                 center = true);
    }
}

// =========================================================================
// LID (top clamshell band) + carry handle
// =========================================================================
module lid() {
    z0 = body_h + lid_open;
    color(C_KHAKI)
    translate([0, 0, z0])
    difference() {
        // lid band sits on the body; chamfered top
        translate([0, 0, 0]) rugged_box(case_w, case_d, lid_h);
        // hollow underside so it reads as a lid, not a solid cap
        translate([0, 0, -eps])
            cube([case_w - 2*wall_thk, case_d - 2*wall_thk,
                  (lid_h - wall_thk) * 2], center = true);
    }
    if (show_handle) translate([0, 0, z0 + lid_h]) carry_handle();
}

// Carry handle: a U-bar bridging across the top in Y.
module carry_handle() {
    span = case_w * 0.5;
    r    = handle_d / 2;
    rise = handle_rise;
    color(C_DARK) {
        // two uprights (overlap into the lid for a solid join)
        for (sy = [-1, 1])
            translate([0, sy * span/2, -6])
                cylinder(h = rise + 6, d = handle_d);
        // top bar
        translate([0, 0, rise])
            rotate([90, 0, 0])
                cylinder(h = span + handle_d, d = handle_d, center = true);
        // rounded corners (spheres fuse the bar to the uprights)
        for (sy = [-1, 1])
            translate([0, sy * span/2, rise]) sphere(r = r);
    }
}

// =========================================================================
// FRONT PANEL — assembled as ADDED bosses, with cutouts subtracted from
// the whole front assembly so cuts pass cleanly through plates + body wall.
// Layout on the +X front face (Y = left<->right, Z = up):
//   LEFT zone  : large 7" touchscreen, vertically centred.
//   RIGHT zone : (top) WRITE-BLOCKER module w/ microSD+SD slots + green LED,
//                (mid) START + EJECT buttons + status-LED row + key-lock.
//   BOTTOM     : printer paper-exit slot + tear bar (under the right zone).
// All features stay well inside the face so the centre is populated, not bare.
// =========================================================================

// --- usable front-face rectangle (Y = left/right, Z = up) ---
fp_y0   = -case_w/2 + panel_margin;     // operator-left edge  (-Y)
fp_y1   =  case_w/2 - panel_margin;     // operator-right edge (+Y)
fp_z0   =  wall_thk + panel_margin;     // bottom edge
fp_z1   =  body_h - panel_margin;       // top edge (bosses live on the body band)

bz_proud = panel_recess + 3;            // how far bosses stand proud of the face

// Two columns kept in a CENTRAL band so a single 3/4 view shows everything.
// LEFT column = touchscreen; RIGHT column = write-blocker + controls + printer.
screen_zone_w = scr_w + 2*screen_bezel + 20;      // Y-width the screen needs
right_zone_w  = max(wb_block_w, paper_slot_w + 20) + 24;
gap           = 26;
band_w        = screen_zone_w + gap + right_zone_w;
band_y0       = -band_w/2;                          // left edge of the central band
// column centres (Y)
scr_cy   = band_y0 + screen_zone_w/2;
right_cy = band_y0 + screen_zone_w + gap + right_zone_w/2;

// Touchscreen: vertically centred on the face
scr_cz  = (fp_z0 + fp_z1)/2;

// Write-blocker module: top of the RIGHT column
wb_cy   = right_cy;
wb_cz   = fp_z1 - wb_block_h/2 - 4;

// Control cluster (buttons + LED row + keylock): middle of the RIGHT column
clu_cy  = right_cy;
clu_cz  = wb_cz - wb_block_h/2 - 30;

// Printer paper-exit: bottom of the RIGHT column
pr_cy   = right_cy;
pr_cz   = fp_z0 + paper_slot_h/2 + 8;

// ---- Front-panel ADDED geometry (bosses/bezels that stand proud) ----
module front_bosses() {
    t  = bz_proud;
    fx = front_x;
    // bosses are seated INTO the face (overlap by 'seat' so they fuse solidly to
    // the wall, no coincident faces) and stand 't' proud of the front plane.
    seat = wall_thk + edge_cham;          // depth the boss reaches back into the body
    bx   = fx + t/2 - seat/2;             // boss centre X (spans [fx-seat, fx+t])
    bt   = t + seat;                      // boss X-thickness

    // Touchscreen bezel frame (proud dark border around the glass)
    color(C_DARK)
        translate([bx, scr_cy, scr_cz])
            cube([bt, scr_w + 2*screen_bezel, scr_h + 2*screen_bezel],
                 center = true);

    // Write-blocker module: labelled raised steel block
    color(C_STEEL)
        translate([bx, wb_cy, wb_cz])
            cube([bt, wb_block_w, wb_block_h], center = true);
    // WRITE-BLOCKER status-LED boss (green = blocked) on the block, by the slots
    color(C_LED_G)
        translate([fx + t, wb_cy + wb_block_w/2 - 12, wb_cz + wb_block_h/2 - 12])
            rotate([0, 90, 0]) cylinder(h = 8, d = led_dia, center = true);

    // Printer paper-exit surround (dark bezel) + alu tear bar above the slot
    color(C_DARK)
        translate([bx, pr_cy, pr_cz + 2])
            cube([bt, paper_slot_w + 18, paper_slot_h + 22], center = true);
    color(C_ALU)
        translate([fx + t, pr_cy, pr_cz + paper_slot_h/2 + 5])
            cube([6, paper_slot_w + 10, 3], center = true);

    // START (green) + EJECT (amber) pushbutton bosses, side by side
    for (i = [0, 1])
        color(i == 0 ? C_LED_G : C_LED_A)
            translate([fx + t, clu_cy + (i == 0 ? 1 : -1)*(btn_dia/2 + 8),
                       clu_cz + 14])
                rotate([0, 90, 0]) cylinder(h = 10, d = btn_dia, center = true);

    // Row of status-LED bosses (centred under the buttons)
    led_pitch = led_dia + 6;
    for (i = [0 : led_count - 1])
        color(i % 2 == 0 ? C_LED_A : C_LED_G)
            translate([fx + t,
                       clu_cy + (led_count - 1)*led_pitch/2 - i*led_pitch,
                       clu_cz - 8])
                rotate([0, 90, 0]) cylinder(h = 8, d = led_dia, center = true);

    // Key-lock (tamper) cylinder boss, lower in the column
    color(C_ALU)
        translate([fx + t, clu_cy, clu_cz - 26])
            rotate([0, 90, 0]) cylinder(h = 11, d = keylock_dia, center = true);
}

// ---- Front-panel CUTOUTS (subtracted) — punch all the way through ----
module front_cutouts() {
    fx    = front_x;
    cut_t = bz_proud + wall_thk + 10;     // overcut so it's a clean through-hole

    // Touchscreen active-glass window
    translate([fx + 2, scr_cy, scr_cz])
        rotate([0, 90, 0]) cube([scr_h, scr_w, cut_t], center = true);

    // Write-blocker: microSD slot (upper) + full-size SD slot (lower)
    translate([fx + 2, wb_cy - 8, wb_cz + 10])
        rotate([0, 90, 0]) cube([usd_slot_h, usd_slot_w, cut_t], center = true);
    translate([fx + 2, wb_cy - 8, wb_cz - 6])
        rotate([0, 90, 0]) cube([sd_slot_h, sd_slot_w, cut_t], center = true);

    // Printer paper-exit slot
    translate([fx + 2, pr_cy, pr_cz])
        rotate([0, 90, 0]) cube([paper_slot_h, paper_slot_w, cut_t], center = true);
}

// =========================================================================
// INTERNAL SUBSYSTEM MASSING
// =========================================================================

// SBC carrier (CM4 carrier / NUC-class) on standoffs, near the rear floor.
module sbc_assembly() {
    bx = -case_d/2 + sbc_board_d/2 + wall_thk + 18;   // toward rear
    by = -case_w/2 + sbc_board_w/2 + wall_thk + 16;
    bz = wall_thk;
    // standoffs
    color(C_ALU)
        for (sx = [-1, 1], sy = [-1, 1])
            translate([bx + sx*(sbc_board_d/2 - 6),
                       by + sy*(sbc_board_w/2 - 6), bz])
                cylinder(h = sbc_standoff, d = 6);
    // carrier PCB
    color(C_PCB)
        translate([bx, by, bz + sbc_standoff])
            cube([sbc_board_d, sbc_board_w, 2.4], center = true);
    // SoM / heatsink massing
    color(C_DARK)
        translate([bx, by, bz + sbc_standoff + 12])
            cube([sbc_board_d*0.5, sbc_board_w*0.55, 20], center = true);
}

// Write-blocker PCB, mounted right behind the front write-blocker module.
module writeblocker_pcb() {
    bx = front_x - wall_thk - 34;
    by = wb_cy;
    bz = wb_cz - 6;
    color(C_PCB)
        translate([bx, by, bz])
            cube([54, wb_block_w * 0.8, 2.4], center = true);
    // bridge connector massing forward to the panel block (solid overlap)
    color(C_DARK)
        translate([bx + 22, by - 14, bz])
            cube([40, 22, 14], center = true);
}

// Built-in 80 mm thermal printer body + paper roll, behind the exit slot.
module printer_assembly() {
    bx = front_x - wall_thk - printer_bay_h/2 - 6;   // depth into case
    by = pr_cy;
    bz = pr_cz + printer_bay_h/2 - paper_slot_h/2 - 8;
    // printer body
    color(C_DARK)
        translate([bx, by, bz])
            cube([printer_bay_h, printer_bay_w, printer_bay_h], center = true);
    // paper roll cylinder (axis along Y), sits above/behind the head
    color(C_PAPER)
        translate([bx - 6, by, bz + printer_bay_h/2 - roll_od/2 + 4])
            rotate([90, 0, 0]) cylinder(h = 80, d = roll_od, center = true);
    // roll core
    color(C_DARK)
        translate([bx - 6, by, bz + printer_bay_h/2 - roll_od/2 + 4])
            rotate([90, 0, 0]) cylinder(h = 82, d = roll_od * 0.25, center = true);
    // feed throat from head down to the exit slot (solid bridge to panel)
    color(C_ALU)
        translate([(bx + front_x)/2, by, pr_cz])
            cube([abs(front_x - bx) + 4, paper_slot_w, paper_slot_h + 2],
                 center = true);
}

// Cooling fan, mounted on the rear inner wall.
module cooling_fan() {
    bx = -case_d/2 + wall_thk + 6;
    by = case_w/2 - wall_thk - fan_dia/2 - 14;
    bz = body_h/2;
    color(C_DARK)
        translate([bx, by, bz])
            rotate([0, 90, 0])
                difference() {
                    cube([fan_dia, fan_dia, 16], center = true);
                    cylinder(h = 20, d = fan_dia - 6, center = true);
                }
    // hub + blades massing
    color(C_STEEL)
        translate([bx, by, bz]) rotate([0, 90, 0]) cylinder(h = 10, d = fan_dia*0.4, center = true);
}

// UPS / battery block on the floor (gives the kiosk field autonomy).
module ups_block() {
    bw = case_w * 0.30;
    bd = case_d * 0.34;
    bh = 46;
    bx = -case_d/2 + bd/2 + wall_thk + 10;
    by = case_w/2 - bw/2 - wall_thk - 10;
    color([0.16, 0.16, 0.15])
        translate([bx, by, wall_thk + bh/2])
            cube([bd, bw, bh], center = true);
    // battery label strip
    color(C_KHAKI)
        translate([bx + bd/2 - 2, by, wall_thk + bh/2])
            cube([3, bw*0.7, bh*0.5], center = true);
}

module internals() {
    sbc_assembly();
    writeblocker_pcb();
    printer_assembly();
    cooling_fan();
    ups_block();
}

// =========================================================================
// REAR PANEL — ports + vents (cut into the rear wall, bosses added outside)
// =========================================================================
module rear_ports() {
    rx = -case_d/2;                 // rear outer plane
    cz = body_h * 0.5;
    // spacing along Y
    function py(i) = -case_w/2 + panel_margin + 26 + i*46;

    // --- added port bezels (proud, on the outside) ---
    // power inlet (IEC-ish)
    color(C_DARK)
        translate([rx - 4, py(0), cz + 26]) rotate([0, 90, 0])
            cube([26, 32, 8], center = true);
    // Ethernet jack
    color(C_STEEL)
        translate([rx - 4, py(1), cz + 26]) rotate([0, 90, 0])
            cube([16, 18, 8], center = true);
    // EVIDENCE USB (write-once export) — labelled khaki boss
    color(C_KHAKI)
        translate([rx - 4, py(2), cz + 26]) rotate([0, 90, 0])
            cube([16, 22, 8], center = true);
    // Kensington-style lock slot housing
    color(C_ALU)
        translate([rx - 4, py(3), cz - 20]) rotate([0, 90, 0])
            cube([11, 7, 8], center = true);
}

// rear cutouts (subtracted) — punch through the rear wall
module rear_cutouts() {
    rx = -case_d/2;
    cz = body_h * 0.5;
    cut_t = wall_thk + 10;
    function py(i) = -case_w/2 + panel_margin + 26 + i*46;

    // power inlet aperture
    translate([rx + 2, py(0), cz + 26]) rotate([0, 90, 0])
        cube([22, 28, cut_t], center = true);
    // Ethernet aperture
    translate([rx + 2, py(1), cz + 26]) rotate([0, 90, 0])
        cube([13.5, 15, cut_t], center = true);
    // Evidence USB aperture
    translate([rx + 2, py(2), cz + 26]) rotate([0, 90, 0])
        cube([13, 6, cut_t], center = true);
    // Kensington slot
    translate([rx + 2, py(3), cz - 20]) rotate([0, 90, 0])
        cube([7, 3, cut_t], center = true);

    // vent louvres (horizontal slots across the upper rear)
    for (i = [0 : vent_louvres - 1])
        translate([rx + 2, case_w*0.18, body_h*0.30 + i*9])
            rotate([0, 90, 0])
                cube([3.0, case_w*0.40, cut_t], center = true);
}

// =========================================================================
// ASSEMBLY
// =========================================================================
module forensiq_appliance() {
    // Lower body with ALL face cutouts subtracted in one difference so cuts
    // pass cleanly through panel bosses AND the structural wall (no coincident
    // faces, no zero-thickness contact -> stays 2-manifold).
    difference() {
        union() {
            body();
            front_bosses();
            rear_ports();
        }
        front_cutouts();
        rear_cutouts();
    }

    // Lid + handle (separate solid, lifts with lid_open)
    lid();

    // Screen glass pane set into the touchscreen window
    color(C_GLASS)
        translate([front_x - wall_thk/2 - 1, scr_cy, scr_cz])
            rotate([0, 90, 0]) cube([scr_h, scr_w, 2], center = true);

    if (show_internals) internals();
}

forensiq_appliance();
