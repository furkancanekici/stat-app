import math
import re
import uuid as _uuid

_B64 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"

STATUS_COLORS_RGB = {
    "OK":        (0.133, 0.773, 0.369),
    "WARNING":   (0.918, 0.702, 0.031),
    "FAIL":      (0.937, 0.267, 0.267),
    "BRITTLE":   (0.976, 0.588, 0.086),
    "UNMATCHED": (0.392, 0.455, 0.545),
}


def _ifc_guid():
    u = _uuid.uuid4().int
    chars = []
    for _ in range(22):
        chars.append(_B64[u % 64])
        u //= 64
    return "".join(chars)


def _f(val):
    if isinstance(val, int):
        return f"{val}."
    if val == int(val):
        return f"{int(val)}."
    return f"{val}"


def _parse_section(name):
    """Kesit adından metre cinsinden (width, height) döndürür."""
    if not name:
        return 0.3, 0.3
    s = name.strip().upper()
    # Column400x300 (mm)
    m = re.match(r"COLUMN\s*(\d+)\s*[Xx]\s*(\d+)", s)
    if m:
        return int(m.group(1)) / 1000, int(m.group(2)) / 1000
    # C30X30 (cm)
    m = re.match(r"C\s*(\d+)\s*[Xx]\s*(\d+)", s)
    if m:
        return int(m.group(1)) / 100, int(m.group(2)) / 100
    # W14X48 (AISC inch)
    m = re.match(r"W\s*(\d+)\s*[Xx]\s*(\d+)", s)
    if m:
        d = int(m.group(1)) * 0.0254
        return d * 0.6, d
    # HEB300 etc
    m = re.match(r"(?:HE|IPE|HEB|HEA)\s*(\d+)", s)
    if m:
        h = int(m.group(1)) / 1000
        return h * 0.5, h
    return 0.3, 0.3


class _IdGen:
    def __init__(self, start=100):
        self._id = start
    def next(self):
        v = self._id
        self._id += 1
        return v


def write_enriched_ifc(elements: list[dict], connectivity: dict) -> bytes:
    lines = []
    def add(s):
        lines.append(s)

    eid = _IdGen(100)
    points = connectivity.get("points", {})
    beam_conn = connectivity.get("beams", {})
    col_conn = connectivity.get("columns", {})

    # ================= HEADER =================
    add("ISO-10303-21;")
    add("HEADER;")
    add("FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');")
    add("FILE_NAME('enriched.ifc','2024-01-01T00:00:00',(''),(''),'STAT App','','');")
    add("FILE_SCHEMA(('IFC2X3'));")
    add("ENDSEC;")
    add("DATA;")

    # ================= CORE =================
    add("#1=IFCORGANIZATION($,'STAT',$,$,$);")
    add("#2=IFCPERSON($,'STAT','App',$,$,$,$,$);")
    add("#3=IFCPERSONANDORGANIZATION(#2,#1,$);")
    add("#4=IFCAPPLICATION(#1,'1.0','STAT App','STAT');")
    add("#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,#3,#4,0);")

    add("#10=IFCDIRECTION((1.,0.,0.));")
    add("#11=IFCDIRECTION((0.,1.,0.));")
    add("#12=IFCDIRECTION((0.,0.,1.));")
    add("#13=IFCCARTESIANPOINT((0.,0.,0.));")
    add("#14=IFCAXIS2PLACEMENT3D(#13,#12,#10);")
    add("#15=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#14,$);")

    # 2D origin for profiles
    add("#30=IFCCARTESIANPOINT((0.,0.));")
    add("#31=IFCDIRECTION((1.,0.));")
    add("#32=IFCAXIS2PLACEMENT2D(#30,#31);")

    # Project / Site / Building
    add(f"#20=IFCPROJECT('{_ifc_guid()}',#5,'STAT Model',$,$,$,$,(#15),$);")
    add(f"#21=IFCSITE('{_ifc_guid()}',#5,'Site',$,$,#14,$,$,.ELEMENT.,$,$,$,$,$);")
    add(f"#22=IFCBUILDING('{_ifc_guid()}',#5,'Building',$,$,#14,$,$,.ELEMENT.,$,$,$);")
    add(f"#23=IFCRELAGGREGATES('{_ifc_guid()}',#5,$,$,#20,(#21));")
    add(f"#24=IFCRELAGGREGATES('{_ifc_guid()}',#5,$,$,#21,(#22));")

    # ================= STATUS RENK TANIMLARI =================
    # Her status için IfcColourRgb + IfcSurfaceStyleRendering + IfcSurfaceStyle
    # + IfcPresentationStyleAssignment oluştur
    style_map = {}  # status -> styled_item_style_id (presentation style assignment)
    for status, (r, g, b) in STATUS_COLORS_RGB.items():
        c_id = eid.next()
        add(f"#{c_id}=IFCCOLOURRGB($,{_f(r)},{_f(g)},{_f(b)});")
        ssr_id = eid.next()
        add(f"#{ssr_id}=IFCSURFACESTYLERENDERING(#{c_id},.BOTH.,$,$,$,$,$,$,.FLAT.);")
        ss_id = eid.next()
        add(f"#{ss_id}=IFCSURFACESTYLE('{status}',.BOTH.,(#{ssr_id}));")
        psa_id = eid.next()
        add(f"#{psa_id}=IFCPRESENTATIONSTYLEASSIGNMENT((#{ss_id}));")
        style_map[status] = psa_id

    # ================= PROFILES =================
    # Profilleri cache'le — aynı boyutlar için tekrar oluşturma
    profile_cache = {}

    def get_profile(w_m, h_m):
        key = (round(w_m, 4), round(h_m, 4))
        if key in profile_cache:
            return profile_cache[key]
        p_id = eid.next()
        add(f"#{p_id}=IFCRECTANGLEPROFILEDEF(.AREA.,$,#32,{_f(w_m)},{_f(h_m)});")
        profile_cache[key] = p_id
        return p_id

    # ================= STORIES =================
    stories = sorted(set(el.get("ifc_story", "") for el in elements if el.get("ifc_story")))
    story_elevs = {}
    story_ids = {}

    for i, sname in enumerate(stories):
        elev = i * 3.0
        cp = eid.next()
        ap = eid.next()
        st = eid.next()
        add(f"#{cp}=IFCCARTESIANPOINT((0.,0.,{_f(elev)}));")
        add(f"#{ap}=IFCAXIS2PLACEMENT3D(#{cp},#12,#10);")
        add(f"#{st}=IFCBUILDINGSTOREY('{_ifc_guid()}',#5,'{sname}',$,$,#{ap},$,$,.ELEMENT.,{_f(elev)});")
        story_ids[sname] = st
        story_elevs[sname] = elev

    storey_refs = ",".join(f"#{v}" for v in story_ids.values())
    agg_id = eid.next()
    add(f"#{agg_id}=IFCRELAGGREGATES('{_ifc_guid()}',#5,$,$,#22,({storey_refs}));")

    # ================= ELEMENTS =================
    rc_members = {s: [] for s in stories}

    for el in elements:
        label = el.get("ifc_name", "")
        story = el.get("ifc_story", "")
        el_type = el.get("ifc_type", "IfcBeam")
        status = el.get("status", "UNMATCHED")
        uc = el.get("unity_check") or 0.0
        fm = el.get("failure_mode", "")
        combo = str(el.get("governing_combo", "")).replace("'", "")
        score = el.get("match_score") or 0.0
        section = el.get("excel_section", "")
        guid = el.get("ifc_global_id", _ifc_guid())
        if len(guid) != 22:
            guid = _ifc_guid()

        elev = story_elevs.get(story, 0.0)

        # ---- Coordinates ----
        if el_type == "IfcBeam" and label in beam_conn:
            pi_lbl = beam_conn[label]["pi"]
            pj_lbl = beam_conn[label]["pj"]
            if pi_lbl in points and pj_lbl in points:
                x1, y1, z1 = points[pi_lbl]["x"], points[pi_lbl]["y"], elev + 3.0
                x2, y2, z2 = points[pj_lbl]["x"], points[pj_lbl]["y"], elev + 3.0
            else:
                x1, y1, z1 = 0., 0., elev + 3.0
                x2, y2, z2 = 1., 0., elev + 3.0
        elif el_type == "IfcColumn" and label in col_conn:
            pi_lbl = col_conn[label]["pi"]
            if pi_lbl in points:
                x1, y1 = points[pi_lbl]["x"], points[pi_lbl]["y"]
                z1, z2 = elev, elev + 3.0
                x2, y2 = x1, y1
            else:
                x1, y1, z1 = 0., 0., elev
                x2, y2, z2 = 0., 0., elev + 3.0
        else:
            x1, y1, z1 = 0., 0., elev
            x2, y2, z2 = 1., 0., elev

        dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        if length < 0.001:
            length = 1.0
            dx, dy, dz = 0., 0., 1.
        ndx, ndy, ndz = dx/length, dy/length, dz/length

        # ---- Profile (gerçek kesit boyutu) ----
        sec_w, sec_h = _parse_section(section)
        profile = get_profile(sec_w, sec_h)

        # ---- Body: extrude along local Z ----
        ext_pos_cp = eid.next()
        ext_pos = eid.next()
        add(f"#{ext_pos_cp}=IFCCARTESIANPOINT((0.,0.,0.));")
        add(f"#{ext_pos}=IFCAXIS2PLACEMENT3D(#{ext_pos_cp},#12,#10);")

        ext = eid.next()
        add(f"#{ext}=IFCEXTRUDEDAREASOLID(#{profile},#{ext_pos},#12,{_f(length)});")

        # ---- StyledItem (renk) ----
        psa_id = style_map.get(status, style_map.get("UNMATCHED"))
        styled = eid.next()
        add(f"#{styled}=IFCSTYLEDITEM(#{ext},(#{psa_id}),$);")

        body_rep = eid.next()
        add(f"#{body_rep}=IFCSHAPEREPRESENTATION(#15,'Body','SweptSolid',(#{ext}));")

        prod_def = eid.next()
        add(f"#{prod_def}=IFCPRODUCTDEFINITIONSHAPE($,$,(#{body_rep}));")

        # ---- LocalPlacement ----
        lp_cp = eid.next()
        add(f"#{lp_cp}=IFCCARTESIANPOINT(({_f(x1)},{_f(y1)},{_f(z1)}));")

        lp_axis = eid.next()
        add(f"#{lp_axis}=IFCDIRECTION(({_f(ndx)},{_f(ndy)},{_f(ndz)}));")

        ref_x, ref_y, ref_z = _perpendicular(ndx, ndy, ndz)
        lp_ref = eid.next()
        add(f"#{lp_ref}=IFCDIRECTION(({_f(ref_x)},{_f(ref_y)},{_f(ref_z)}));")

        lp_ax = eid.next()
        add(f"#{lp_ax}=IFCAXIS2PLACEMENT3D(#{lp_cp},#{lp_axis},#{lp_ref});")

        lp = eid.next()
        add(f"#{lp}=IFCLOCALPLACEMENT($,#{lp_ax});")

        # ---- Element ----
        el_id = eid.next()
        if el_type == "IfcColumn":
            add(f"#{el_id}=IFCCOLUMN('{guid}',#5,'{label}',$,'Column',#{lp},#{prod_def},'{label}');")
        else:
            add(f"#{el_id}=IFCBEAM('{guid}',#5,'{label}',$,'Beam',#{lp},#{prod_def},'{label}');")

        # ---- Property Set ----
        pv1 = eid.next(); pv2 = eid.next(); pv3 = eid.next()
        pv4 = eid.next(); pv5 = eid.next()
        ps = eid.next(); rp = eid.next()
        add(f"#{pv1}=IFCPROPERTYSINGLEVALUE('Status',$,IFCLABEL('{status}'),$);")
        add(f"#{pv2}=IFCPROPERTYSINGLEVALUE('UnityCheck',$,IFCREAL({uc}),$);")
        add(f"#{pv3}=IFCPROPERTYSINGLEVALUE('FailureMode',$,IFCLABEL('{fm}'),$);")
        add(f"#{pv4}=IFCPROPERTYSINGLEVALUE('GoverningCombo',$,IFCLABEL('{combo}'),$);")
        add(f"#{pv5}=IFCPROPERTYSINGLEVALUE('MatchScore',$,IFCREAL({score}),$);")
        add(f"#{ps}=IFCPROPERTYSET('{_ifc_guid()}',#5,'STAT_Analysis',$,(#{pv1},#{pv2},#{pv3},#{pv4},#{pv5}));")
        add(f"#{rp}=IFCRELDEFINESBYPROPERTIES('{_ifc_guid()}',#5,$,$,(#{el_id}),#{ps});")

        if story in rc_members:
            rc_members[story].append(el_id)

    # ================= SPATIAL CONTAINMENT =================
    for i, story in enumerate(stories):
        if rc_members[story]:
            members = ",".join(f"#{e}" for e in rc_members[story])
            st_id = story_ids[story]
            rc_id = eid.next()
            add(f"#{rc_id}=IFCRELCONTAINEDINSPATIALSTRUCTURE('{_ifc_guid()}',#5,$,$,({members}),#{st_id});")

    add("ENDSEC;")
    add("END-ISO-10303-21;")
    return "\n".join(lines).encode("utf-8")


def _perpendicular(dx, dy, dz):
    ax, ay, az = abs(dx), abs(dy), abs(dz)
    if ax <= ay and ax <= az:
        hx, hy, hz = 1., 0., 0.
    elif ay <= az:
        hx, hy, hz = 0., 1., 0.
    else:
        hx, hy, hz = 0., 0., 1.
    rx = hy * dz - hz * dy
    ry = hz * dx - hx * dz
    rz = hx * dy - hy * dx
    rl = math.sqrt(rx*rx + ry*ry + rz*rz)
    if rl < 1e-10:
        return (1., 0., 0.)
    return (round(rx/rl, 6), round(ry/rl, 6), round(rz/rl, 6))