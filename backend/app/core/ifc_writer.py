import math
import uuid as _uuid


STATUS_COLORS = {
    "OK":        (0.133, 0.773, 0.369),
    "WARNING":   (0.918, 0.702, 0.031),
    "FAIL":      (0.937, 0.267, 0.267),
    "BRITTLE":   (0.976, 0.588, 0.086),
    "UNMATCHED": (0.392, 0.361, 0.478),
}

# IFC Base64 charset (standart)
_B64 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"


def _ifc_guid():
    """IFC uyumlu 22 karakterlik GlobalId üretir (UUID4 → Base64)."""
    u = _uuid.uuid4().int
    chars = []
    for _ in range(22):
        chars.append(_B64[u % 64])
        u //= 64
    return "".join(chars)


def _f(val):
    """IFC uyumlu float: 5.0→'5.', 3.14→'3.14', 0.0→'0.'"""
    if isinstance(val, int):
        return f"{val}."
    if val == int(val):
        return f"{int(val)}."
    return f"{val}"


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

    # ===================== HEADER =====================
    add("ISO-10303-21;")
    add("HEADER;")
    add("FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');")
    add("FILE_NAME('enriched.ifc','2024-01-01T00:00:00',(''),(''),'STAT App','','');")
    add("FILE_SCHEMA(('IFC2X3'));")
    add("ENDSEC;")
    add("DATA;")

    # ===================== TEMEL TANIMLAR =====================
    add(f"#1=IFCORGANIZATION($,'STAT',$,$,$);")
    add(f"#2=IFCPERSON($,'STAT','App',$,$,$,$,$);")
    add(f"#3=IFCPERSONANDORGANIZATION(#2,#1,$);")
    add(f"#4=IFCAPPLICATION(#1,'1.0','STAT App','STAT');")
    add(f"#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,#3,#4,0);")

    add("#10=IFCDIRECTION((1.,0.,0.));")
    add("#11=IFCDIRECTION((0.,1.,0.));")
    add("#12=IFCDIRECTION((0.,0.,1.));")
    add("#13=IFCCARTESIANPOINT((0.,0.,0.));")
    add("#14=IFCAXIS2PLACEMENT3D(#13,#12,#10);")
    add("#15=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#14,$);")

    add(f"#20=IFCPROJECT('{_ifc_guid()}',#5,'STAT Model',$,$,$,$,(#15),$);")
    add(f"#21=IFCSITE('{_ifc_guid()}',#5,'Site',$,$,#14,$,$,.ELEMENT.,$,$,$,$,$);")
    add(f"#22=IFCBUILDING('{_ifc_guid()}',#5,'Building',$,$,#14,$,$,.ELEMENT.,$,$,$);")
    add(f"#23=IFCRELAGGREGATES('{_ifc_guid()}',#5,$,$,#20,(#21));")
    add(f"#24=IFCRELAGGREGATES('{_ifc_guid()}',#5,$,$,#21,(#22));")

    # ===================== PROFİL TANIMLARI =====================
    beam_prof = eid.next()
    add(f"#{beam_prof}=IFCRECTANGLEPROFILEDEF(.AREA.,'BeamProfile',$,0.3,0.3);")

    col_prof = eid.next()
    add(f"#{col_prof}=IFCRECTANGLEPROFILEDEF(.AREA.,'ColProfile',$,0.3,0.3);")

    # ===================== KATLAR =====================
    stories = sorted(set(
        el.get("ifc_story", "") for el in elements if el.get("ifc_story")
    ))
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

    # ===================== ELEMANLAR =====================
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
        guid = el.get("ifc_global_id", _ifc_guid())

        # GUID 22 karakter değilse yeniden üret
        if len(guid) != 22:
            guid = _ifc_guid()

        elev = story_elevs.get(story, 0.0)

        # ---- Koordinat hesapla ----
        if el_type == "IfcBeam" and label in beam_conn:
            pi_lbl = beam_conn[label]["pi"]
            pj_lbl = beam_conn[label]["pj"]
            if pi_lbl in points and pj_lbl in points:
                x1 = points[pi_lbl]["x"]
                y1 = points[pi_lbl]["y"]
                z1 = elev + 3.0
                x2 = points[pj_lbl]["x"]
                y2 = points[pj_lbl]["y"]
                z2 = elev + 3.0
            else:
                x1, y1, z1 = 0., 0., elev + 3.0
                x2, y2, z2 = 1., 0., elev + 3.0
        elif el_type == "IfcColumn" and label in col_conn:
            pi_lbl = col_conn[label]["pi"]
            if pi_lbl in points:
                x1 = points[pi_lbl]["x"]
                y1 = points[pi_lbl]["y"]
                z1 = elev
                x2 = x1
                y2 = y1
                z2 = elev + 3.0
            else:
                x1, y1, z1 = 0., 0., elev
                x2, y2, z2 = 0., 0., elev + 3.0
        else:
            x1, y1, z1 = 0., 0., elev
            x2, y2, z2 = 1., 0., elev

        dx = x2 - x1
        dy = y2 - y1
        dz = z2 - z1
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        if length < 0.001:
            length = 1.0
            dx, dy, dz = 1., 0., 0.

        ndx = dx / length
        ndy = dy / length
        ndz = dz / length

        # ---- Axis representation ----
        p1 = eid.next()
        p2 = eid.next()
        poly = eid.next()
        ax_rep = eid.next()
        add(f"#{p1}=IFCCARTESIANPOINT((0.,0.,0.));")
        add(f"#{p2}=IFCCARTESIANPOINT(({_f(length)},0.,0.));")
        add(f"#{poly}=IFCPOLYLINE((#{p1},#{p2}));")
        add(f"#{ax_rep}=IFCSHAPEREPRESENTATION(#15,'Axis','Curve3D',(#{poly}));")

        # ---- Body representation ----
        profile = col_prof if el_type == "IfcColumn" else beam_prof
        ext_dir = "#12" if el_type == "IfcColumn" else "#10"

        ext = eid.next()
        add(f"#{ext}=IFCEXTRUDEDAREASOLID(#{profile},#14,{ext_dir},{_f(length)});")

        body_rep = eid.next()
        add(f"#{body_rep}=IFCSHAPEREPRESENTATION(#15,'Body','SweptSolid',(#{ext}));")

        prod_def = eid.next()
        add(f"#{prod_def}=IFCPRODUCTDEFINITIONSHAPE($,$,(#{ax_rep},#{body_rep}));")

        # ---- Local Placement ----
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

        # ---- Element entity ----
        el_id = eid.next()
        if el_type == "IfcColumn":
            add(f"#{el_id}=IFCCOLUMN('{guid}',#5,'{label}',$,'Column',#{lp},#{prod_def},'{label}');")
        else:
            add(f"#{el_id}=IFCBEAM('{guid}',#5,'{label}',$,'Beam',#{lp},#{prod_def},'{label}');")

        # ---- STAT_Analysis PropertySet ----
        pv1 = eid.next()
        pv2 = eid.next()
        pv3 = eid.next()
        pv4 = eid.next()
        pv5 = eid.next()
        ps = eid.next()
        rp = eid.next()

        add(f"#{pv1}=IFCPROPERTYSINGLEVALUE('Status',$,IFCLABEL('{status}'),$);")
        add(f"#{pv2}=IFCPROPERTYSINGLEVALUE('UnityCheck',$,IFCREAL({uc}),$);")
        add(f"#{pv3}=IFCPROPERTYSINGLEVALUE('FailureMode',$,IFCLABEL('{fm}'),$);")
        add(f"#{pv4}=IFCPROPERTYSINGLEVALUE('GoverningCombo',$,IFCLABEL('{combo}'),$);")
        add(f"#{pv5}=IFCPROPERTYSINGLEVALUE('MatchScore',$,IFCREAL({score}),$);")
        add(f"#{ps}=IFCPROPERTYSET('{_ifc_guid()}',#5,'STAT_Analysis',$,(#{pv1},#{pv2},#{pv3},#{pv4},#{pv5}));")
        add(f"#{rp}=IFCRELDEFINESBYPROPERTIES('{_ifc_guid()}',#5,$,$,(#{el_id}),#{ps});")

        if story in rc_members:
            rc_members[story].append(el_id)

    # ===================== SPATIAL CONTAINMENT =====================
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
    """Verilen direction vektörüne dik bir vektör döndürür."""
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