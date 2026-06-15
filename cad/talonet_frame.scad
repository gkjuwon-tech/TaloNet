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
//   - Belly net-launcher bay + winch/release (captured drone carried in the net)
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

/* [Battery] */
batt_w           = 170;    // [80:260]
batt_l           = 210;    // [120:320]
batt_h           = 75;     // [30:140]

/* [Capture net] */
show_net         = true;
net_radius       = 430;    // [200:800] deployed mouth radius (opening)
net_depth        = 560;    // [200:1000] funnel/pocket depth (apex->rim)
net_rings        = 6;      // [3:12] concentric hoops
net_spokes       = 16;     // [6:28] radial cords
net_strut_d      = 3.0;    // [1:6] cord thickness (visual)
net_drop_off     = 30;     // [0:300] apex drop below belly

/* [Cinch: net-mouth drawstring spool] */
// SEPARATE drive from the hoist winch: this motor reels the mouth drawstring
// (perimeter purse-loop) to cinch the net opening shut right after capture.
show_cinch       = true;
cinch_spool_dia  = 38;     // [16:90] drawstring spool flange diameter
cinch_spool_w    = 26;     // [10:60] spool drum width (drawstring capacity)
cinch_motor_dia  = 28;     // [14:50] brushed gearmotor can diameter
cinch_motor_len  = 56;     // [20:100] brushed gearmotor + gearhead length
cinch_pos_x      = 120;    // [-200:200] spool assembly X (belly-mounted)
cinch_drop       = 24;     // [0:120] spool centre below the belly reference plane
cinch_guide_d    = 9;      // [4:20] drawstring guide-eyelet bore

/* [Net aiming gimbal] */
// SOFTWARE-AIMED launcher: pan/tilt servos point the muzzle so the net is THROWN
// where commanded (no longer dropped by gravity/luck). Driven by the GCS.
show_aim         = true;
net_pan          = 0;      // [-60:60] azimuth aim, deg (software-set)
net_tilt         = 16;     // [0:75] tilt from straight-down toward the nose, deg
aim_servo        = 24;     // [14:40] aim-servo block size
gimbal_ring_d    = 92;     // [50:170] pan bearing / tilt-yoke ring diameter

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

// strut between two 3D points
module strut(p0, p1, d = net_strut_d) {
    hull() {
        translate(p0) sphere(d/2, $fn = 12);
        translate(p1) sphere(d/2, $fn = 12);
    }
}

// Deployed capture net: DOWNWARD-opening funnel/canopy with a catching pocket.
// Mothership flies above the target; the net deploys below, apex at the belly
// launcher, mouth flaring downward (-Z) into a wide circle so the target below
// is funnelled into the pocket. Rim weights pull the mouth open.
module capture_net() {
    R   = net_radius;
    D   = net_depth;
    nr  = net_rings;
    ns  = net_spokes;
    za  = -bay_h - net_drop_off;   // apex z (just below belly)
    // ring i in [0..nr], spoke j -> 3D node.
    // radius grows with i; the mouth (i=nr) flares downward with a bell profile.
    function NP(i, j) =
        let (t  = i / nr,
             r  = R * t,
             z  = za - D * (0.15 * t + 0.85 * t * t),   // opens downward
             a  = 360 * j / ns)
        [ 40 + r * cos(a), r * sin(a), z ];
    apex = [40, 0, za];

    color(C_NET) {
        // radial cords: apex -> rim
        for (j = [0 : ns - 1]) {
            strut(apex, NP(1, j));
            for (i = [1 : nr - 1]) strut(NP(i, j), NP(i + 1, j));
        }
        // concentric hoops
        for (i = [1 : nr])
            for (j = [0 : ns - 1])
                strut(NP(i, j), NP(i, (j + 1) % ns));
    }
    // perimeter weights (open the mouth on deployment)
    color(C_DARK)
        for (j = [0 : ns - 1]) translate(NP(nr, j)) sphere(11, $fn = 18);
    // tether: belly muzzle -> net apex
    color([0.3, 0.3, 0.27])
        strut([40, 0, -bay_h], apex, 2.6);
}

// World-space position of net-mouth rim node j (matches capture_net() rim).
// Used so the cinch drawstring routing lands exactly on the mouth perimeter.
function rim_node(j) =
    let (a = 360 * j / net_spokes,
         z = (-bay_h - net_drop_off) - net_depth)   // rim z (i = net_rings)
    [ 40 + net_radius * cos(a), net_radius * sin(a), z ];

// A drawstring guide eyelet (annular ring the purse-line is routed through).
module guide_eye(p, bore = cinch_guide_d) {
    color(C_ALU)
        translate(p) rotate([90, 0, 0])
            difference() {
                cylinder(h = 4, d = bore + 6, center = true, $fn = 28);
                cylinder(h = 6, d = bore,     center = true, $fn = 28);
            }
}

// Net-mouth CINCH drawstring spool — a DEDICATED actuator, separate from the
// hoist winch (winch_release()). Sequence: capture -> THIS motor purses the
// mouth drawstring shut (tension/current threshold = secured) -> winch hauls
// the whole pocket up to the belly. Brushed gearmotor drives a flanged drum;
// two guide eyelets route the purse-line down to the mouth perimeter.
module cinch_mechanism() {
    px = cinch_pos_x;
    pz = -bay_h * 1.5 - cinch_drop; // hangs just below the belly bay bottom
    drum_d  = cinch_spool_dia * 0.55;
    hw      = cinch_spool_w / 2;
    // mounting bracket up into the belly bay underside (straddles + overlaps
    // both the spool and the bay so it is solidly fused, not merely touching)
    color(C_KHAKI)
        translate([px, 0, pz + cinch_spool_dia/2 + cinch_drop/2])
            cube([48, cinch_spool_w + 44, cinch_spool_dia + cinch_drop], center = true);
    // brushed gearmotor can (axis along -Y), couples to the spool drum
    color(C_ALU)
        translate([px, -(hw + cinch_motor_len/2 + 3), pz])
            rotate([90, 0, 0]) cylinder(h = cinch_motor_len, d = cinch_motor_dia, center = true);
    // gearhead collar between motor and spool (overlaps both)
    color(C_DARK)
        translate([px, -(hw + 4), pz])
            rotate([90, 0, 0]) cylinder(h = 16, d = cinch_motor_dia + 6, center = true);
    // spool drum (drawstring winds on here)
    color(C_DARK)
        translate([px, 0, pz])
            rotate([90, 0, 0]) cylinder(h = cinch_spool_w + 2, d = drum_d, center = true);
    // spool flanges (keep wraps from spilling)
    color(C_ALU)
        for (sy = [-1, 1])
            translate([px, sy * hw, pz])
                rotate([90, 0, 0]) cylinder(h = 3, d = cinch_spool_dia, center = true);
    // load/tension pickup housing straddling the outboard flange (load-cell / encoder)
    color(C_KHAKI)
        translate([px, hw + 3, pz])
            rotate([90, 0, 0]) cylinder(h = 16, d = cinch_motor_dia * 0.7, center = true);

    // drawstring routing: spool -> belly fairlead -> mouth perimeter (rim)
    guide_top = [px, 0, pz];                             // line leaves spool from the drum
    guide_bel = [40, 0, -bay_h - 6];                     // belly fairlead near muzzle
    color([0.3, 0.3, 0.27]) {
        guide_eye(guide_bel);
        strut(guide_top, guide_bel, 2.2);
        // purse hauls fan out to opposing rim nodes (the perimeter draw-loop)
        for (j = [0, round(net_spokes/4), round(net_spokes/2), round(3*net_spokes/4)])
            strut(guide_bel, rim_node(j), 2.0);
    }
}

// SOFTWARE-AIMED net launcher: a pan/tilt gimbal points the muzzle so the net
// is thrown where the GCS commands, instead of being dropped by gravity. The
// whole net pod (muzzle nozzle + capture net + cinch spool) rides the aim, so
// changing net_pan/net_tilt swings the deployed net. Two servos (pan + tilt)
// are the visible actuators; the gimbal base bolts to the belly bay.
module net_launcher() {
    pv  = [40, 0, -bay_h];               // gimbal pivot = belly muzzle reference
    rd  = gimbal_ring_d;
    // FIXED base: pan bearing housing + PAN servo (mounted to the bay underside)
    color(C_DARK)
        translate([40, 0, -bay_h + 1]) cylinder(h = 14, d = rd, center = true);
    color(C_KHAKI)
        translate([40, rd/2 + aim_servo*0.55, -bay_h + 1])
            cube([aim_servo*1.4, aim_servo, aim_servo], center = true);   // PAN servo
    // AIMED group: pan about Z, then tilt about Y, about the pivot
    translate(pv) rotate([0, 0, net_pan]) rotate([0, net_tilt, 0]) translate([-40, 0, bay_h]) {
        // pan turntable disc the yoke hangs from
        color(C_ALU)
            translate([40, 0, -bay_h - 6]) cylinder(h = 8, d = rd*0.8, center = true);
        // tilt yoke (two arms) framing the muzzle
        for (sy = [-1, 1])
            color(C_ALU)
                translate([40, sy*rd*0.34, -bay_h - net_drop_off*0.5 - 6])
                    cube([12, 9, net_drop_off + 14], center = true);
        // TILT servo on the +Y yoke arm
        color(C_KHAKI)
            translate([40, rd*0.34 + aim_servo*0.55, -bay_h - net_drop_off*0.5 - 6])
                cube([aim_servo, aim_servo*0.8, aim_servo], center = true);
        // muzzle nozzle (net deploys from here, in the aimed direction)
        color(C_DARK)
            translate([40, 0, -bay_h - net_drop_off]) rotate([90, 0, 0])
                cylinder(h = 10, d = rd*0.55, center = true);
        // the deployed net + the cinch spool ride the aim
        if (show_cinch) cinch_mechanism();
        if (show_net)   capture_net();
    }
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
    if (show_aim) net_launcher();
    else {
        if (show_cinch) cinch_mechanism();
        if (show_net) capture_net();
    }
}

talonet_drone();
