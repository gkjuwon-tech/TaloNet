// =============================================================================
// TaloNet "그물매 (Geulmae)" — parametric mothership frame
// X8 coaxial octocopter counter-UAS net interceptor
//
// Units: millimetres. Coordinate frame: +X = nose/forward, +Z = up.
// Specs traced to docs/01_드론_스펙.md:
//   - X8 coaxial octocopter (4 arms x 2 coaxial motors = 8)
//   - 1150 mm motor-to-motor diagonal wheelbase
//   - 6.8 kg empty / 14 kg MTOW
//   - Jetson Orin companion compute, modular payload bays
//   - Belly net-launcher bay + foldable nest cage + winch/release
//
// This is a DESIGN / visualization model (massing + mounting geometry), not a
// stress-certified manufacturing model. Render STL:  openscad -o frame.stl talonet_frame.scad
// =============================================================================

/* [Airframe] */
// Motor-to-motor diagonal (wheelbase), mm
wheelbase        = 1150;   // [600:1600]
// Number of arms (X8 = 4 arms, 2 coaxial motors each)
arm_count        = 4;      // [3:8]
// Coaxial (true = 2 motors/arm, X8) or flat (false)
coaxial          = true;
// Forward yaw offset of the arm cross (deg). 45 => classic "X" layout
arm_yaw_offset   = 45;     // [0:90]

/* [Arms] */
arm_tube_od      = 30;     // [16:40] carbon tube outer dia
arm_tube_id      = 26;     // [10:38]
arm_clamp_len    = 70;     // [40:120]

/* [Central body] */
plate_across     = 360;    // [200:600] hex plate across-flats
plate_thk        = 6;      // [3:12]
deck_gap         = 70;     // [40:160] gap between bottom/top decks
electronics_h    = 55;     // [30:120] avionics stack height

/* [Propellers] */
prop_dia         = 711;    // [300:900] ~28 in folding props
show_props       = true;

/* [Landing gear] */
gear_height      = 230;    // [120:400]
gear_track       = 520;    // [200:800]
gear_tube_od     = 22;     // [12:30]

/* [Payload: net-launcher bay] */
bay_w            = 240;    // [120:360]
bay_l            = 300;    // [150:420]
bay_h            = 130;    // [60:220]

/* [Nest cage (recovered-drone basket)] */
show_cage        = true;
cage_w           = 360;    // [200:520]
cage_l           = 360;    // [200:520]
cage_h           = 280;    // [150:420]

/* [Battery] */
batt_w           = 170;    // [80:260]
batt_l           = 210;    // [120:320]
batt_h           = 75;     // [30:140]

/* [Capture net] */
show_net         = true;
net_span         = 620;    // [300:1000] deployed net width/depth
net_drop         = 170;    // [40:400] catenary sag at centre
net_cells        = 8;      // [4:14] mesh grid lines per side
net_strut_d      = 3.2;    // [1:6] cord thickness (visual)
net_fwd          = 540;    // [0:900] forward deploy distance from belly
net_z            = -110;   // [-400:0] net top height (rel. lower deck)

/* [Render] */
$fn              = 64;

// ----- derived -----------------------------------------------------------
motor_radius   = wheelbase / 2;                 // center -> motor
plate_r        = plate_across / 2;              // across-flats radius
arm_len        = motor_radius - plate_r * 0.6;  // exposed tube length
deck_z_bot     = 0;
deck_z_top     = deck_gap;

// ----- color helpers -----------------------------------------------------
C_CARBON  = [0.13, 0.13, 0.14];
C_KHAKI   = [0.525, 0.522, 0.373];   // #86855F TaloNet signature khaki
C_ALU     = [0.62, 0.62, 0.60];
C_DARK    = [0.08, 0.08, 0.07];
C_BATT    = [0.18, 0.20, 0.16];
C_NET     = [0.49, 0.49, 0.40];      // capture-net cord (khaki-grey)

// =========================================================================
// MODULES
// =========================================================================

// Hexagonal carbon deck plate with lightening holes
module deck_plate(across = plate_across, thk = plate_thk) {
    color(C_CARBON)
    difference() {
        cylinder(h = thk, d = across, $fn = 6);
        // central cable pass-through
        translate([0, 0, -1]) cylinder(h = thk + 2, d = across * 0.28, $fn = 48);
        // lightening holes around the ring
        for (a = [0 : 60 : 359])
            rotate([0, 0, a]) translate([across * 0.32, 0, -1])
                cylinder(h = thk + 2, d = across * 0.12, $fn = 32);
    }
}

// One motor (can with bell) + optional prop
module motor(with_prop = true) {
    color(C_ALU) cylinder(h = 32, d = 56);            // stator can
    color(C_DARK) translate([0, 0, 32]) cylinder(h = 14, d = 60); // bell
    if (with_prop && show_props)
        color([0.1, 0.1, 0.1, 0.55])
            translate([0, 0, 48]) prop(prop_dia);
}

// Two-blade folding prop disc (visualization)
module prop(dia) {
    for (a = [0, 180])
        rotate([0, 0, a])
            hull() {
                cylinder(h = 4, d = 26);
                translate([dia / 2 - 18, 0, 0]) cylinder(h = 4, d = 34);
            }
}

// Coaxial motor mount at the end of an arm
module motor_mount() {
    // mount block
    color(C_KHAKI) translate([0, 0, -8]) cylinder(h = 16, d = 74);
    // top motor (pusher up)
    translate([0, 0, 8]) motor(true);
    // bottom motor (coaxial, mirrored down)
    if (coaxial)
        translate([0, 0, -8]) mirror([0, 0, 1]) motor(true);
}

// A single arm: clamp + tube + motor mount, laid along +X
module arm() {
    // clamp at root
    color(C_KHAKI) translate([plate_r * 0.6, 0, 0])
        rotate([0, 90, 0]) cylinder(h = arm_clamp_len, d = arm_tube_od + 14, center = true);
    // carbon tube
    color(C_CARBON) translate([plate_r * 0.6, 0, 0])
        rotate([0, 90, 0]) difference() {
            cylinder(h = arm_len, d = arm_tube_od);
            translate([0, 0, -1]) cylinder(h = arm_len + 2, d = arm_tube_id);
        }
    // motor mount at tip
    translate([plate_r * 0.6 + arm_len, 0, 0]) motor_mount();
}

// Avionics stack between the decks (FC + companion + PDB massing)
module avionics_stack() {
    color([0.10, 0.10, 0.11])
        translate([0, 0, plate_thk]) cube([150, 110, electronics_h], center = true);
    // Jetson Orin companion (khaki heatsink massing)
    color(C_KHAKI)
        translate([0, 70, plate_thk + 6]) cube([100, 70, 26], center = true);
}

// Belly net-launcher payload bay (square, pan-tilt cradle)
module netlauncher_bay() {
    color(C_KHAKI)
    translate([40, 0, -bay_h])
    difference() {
        cube([bay_l, bay_w, bay_h], center = true);
        // muzzle aperture (forward/down)
        translate([bay_l/2 - 6, 0, -bay_h/4])
            rotate([0, 90, 0]) cylinder(h = 24, d = bay_w * 0.5, center = true);
        // weight reduction window
        translate([0, 0, 6]) cube([bay_l*0.7, bay_w*0.7, bay_h], center = true);
    }
}

// Winch + electronic quick-release drum under the belly bay
module winch_release() {
    color(C_ALU) translate([40, 0, -bay_h - 18])
        rotate([90, 0, 0]) cylinder(h = 90, d = 40, center = true);
    color(C_KHAKI) translate([40, 0, -bay_h - 42])
        cube([60, 40, 26], center = true);   // release actuator housing
}

// Foldable nest cage (recovered-drone basket) hanging below
module nest_cage() {
    z0 = -bay_h - 60;
    // vertical rods
    for (sx = [-1, 1], sy = [-1, 1])
        color(C_ALU)
        translate([40 + sx * cage_l/2, sy * cage_w/2, z0 - cage_h/2])
            cylinder(h = cage_h, d = 8, center = true);
    // ring frames
    for (zz = [z0, z0 - cage_h])
        color(C_KHAKI)
        translate([40, 0, zz])
        difference() {
            cube([cage_l + 12, cage_w + 12, 8], center = true);
            cube([cage_l - 12, cage_w - 12, 10], center = true);
        }
    // mesh hint (sparse)
    for (i = [-1:0.5:1])
        color([0.2,0.2,0.18,0.5])
        translate([40, i * cage_w/2, z0 - cage_h/2])
            cube([cage_l, 1, cage_h], center = true);
}

// Landing gear: two arch skids
module landing_gear() {
    for (sx = [-1, 1])
        color(C_DARK) {
            // leg
            translate([sx * gear_track/2 * 0.5, 0, -gear_height/2])
                rotate([0, sx*18, 0]) cylinder(h = gear_height, d = gear_tube_od, center = true);
            // skid
            translate([sx * gear_track/2, 0, -gear_height])
                rotate([90, 0, 0]) cylinder(h = bay_w*1.8, d = gear_tube_od, center = true);
        }
}

// Battery pack on the top deck
module battery() {
    color(C_BATT)
        translate([0, 0, deck_z_top + plate_thk + batt_h/2])
            cube([batt_l, batt_w, batt_h], center = true);
}

// ----- net geometry helpers ---------------------------------------------
function net_x(i, n, span) = -span/2 + span * (i / n);
// downward sag (catenary-ish): 0 at edges, -drop at centre
function net_sag(i, j, n, drop) =
    let (u = i/n - 0.5, v = j/n - 0.5)
        -drop * (1 - 4*u*u) * (1 - 4*v*v);

// strut between two 3D points
module strut(p0, p1, d = net_strut_d) {
    hull() {
        translate(p0) sphere(d/2, $fn = 12);
        translate(p1) sphere(d/2, $fn = 12);
    }
}

// Deployed capture net: sagging square mesh + corner weights + tethers
module capture_net() {
    n  = net_cells;
    sp = net_span;
    cx = 40 + net_fwd;     // forward of belly
    // mesh node position
    function P(i, j) = [ cx + net_x(i, n, sp),
                         net_x(j, n, sp),
                         net_z + net_sag(i, j, n, net_drop) ];
    color(C_NET) {
        // cords along X and Y
        for (i = [0 : n], j = [0 : n]) {
            if (i < n) strut(P(i, j), P(i + 1, j));
            if (j < n) strut(P(i, j), P(i, j + 1));
        }
    }
    // corner weights (steel bolos)
    color(C_DARK)
        for (ci = [0, n], cj = [0, n])
            translate(P(ci, cj)) sphere(11, $fn = 20);
    // tethers from belly launcher to the two near corners
    color([0.3, 0.3, 0.27])
        for (cj = [0, n])
            strut([40, net_x(cj, n, sp) * 0.4, -bay_h/2], P(0, cj), 2.4);
}

// =========================================================================
// ASSEMBLY
// =========================================================================
module talonet_drone() {
    // decks
    translate([0, 0, deck_z_bot]) deck_plate();
    translate([0, 0, deck_z_top]) deck_plate();

    // arms radiating out (X layout)
    for (i = [0 : arm_count - 1]) {
        a = arm_yaw_offset + i * (360 / arm_count);
        rotate([0, 0, a])
            translate([0, 0, deck_z_top/2 + plate_thk/2]) arm();
    }

    avionics_stack();
    battery();
    landing_gear();
    netlauncher_bay();
    winch_release();
    if (show_cage) nest_cage();
    if (show_net) capture_net();
}

talonet_drone();
