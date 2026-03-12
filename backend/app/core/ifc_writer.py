import math
from app.utils.normalize import normalize_story


STATUS_COLORS = {
    "OK":        (0.133, 0.773, 0.369),
    "WARNING":   (0.918, 0.702, 0.031),
    "FAIL":      (0.937, 0.267, 0.267),
    "BRITTLE":   (0.976, 0.588, 0.086),
    "UNMATCHED": (0.392, 0.361, 0.478),
}


def _f(val):
    """IFC uyumlu float formatı: 5.0 → '5.' , 0.0 → '0.' , 3.14 → '3.14'"""
    if val == int(val):
        return f"{int(val)}."
    return f"{val}"


def write_enriched_ifc(elements: list[dict], connectivity: dict) -> bytes:
    lines = []
    def add(s): lines.append(s)

    add("ISO-10303-21;")
    add("HEADER;")
    add("FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');")
    add("FILE_NAME('enriched.ifc','2024-01-01T00:00:00',(''),(''),'STAT App','','');")
    add("FILE_SCHEMA(('IFC2X3'));")
    add("ENDSEC;")
    add("DATA;")
    add("#1=IFCORGANIZATION($,'STAT',$,$,$);")
    add("#2=IFCPERSON($,'STAT','App',$,$,$,$,$);")
    add("#3=IFCPERSONANDORGANIZATION(#2,#1,$);")
    add("#4=IFCAPPLICATION(#1,'1.0','STAT App','STAT');")
    add("#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,#3,#4,0);")
    add("#6=IFCDIRECTION((1.,0.,0.));")
    add("#7=IFCDIRECTION((0.,0.,1.));")
    add("#8=IFCCARTESIANPOINT((0.,0.,0.));")
    add("#9=IFCAXIS2PLACEMENT3D(#8,#7,#6);")
    add("#10=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#9,$);")
    add("#11=IFCPROJECT('STATPROJ000000000000000',#5,'STAT Model',$,$,$,$,(#10),$);")
    add("#12=IFCSITE('STATSITE000000000000000',#5,'Site',$,$,#9,$,$,.ELEMENT.,$,$,$,$,$);")
    add("#13=IFCBUILDING('STATBLDG000000000000000',#5,'Building',$,$,#9,$,$,.ELEMENT.,$,$,$);")
    add("#14=IFCRELAGGREGATES('RA01000000000000000000',#5,$,$,#11,(#12));")
    add("#15=IFCRELAGGREGATES('RA02000000000000000000',#5,$,$,#12,(#13));")

    eid = 100
    points = connectivity.get("points", {})

    # --- Profil tanımı (dikdörtgen kesit) ---
    # Kiriş profili: 300x300mm
    beam_profile_pts = eid; eid += 1
    beam_profile = eid; eid += 1
    add(f"#{beam_profile_pts}=IFCCARTESIANPOINT((0.15,0.15));")  # yarı genişlik
    add(f"#{beam_profile}=IFCRECTANGLEPROFILEDEF(.AREA.,$,#{beam_profile_pts},0.3,0.3);")

    # Kolon profili: 300x300mm
    col_profile_pts = eid; eid += 1
    col_profile = eid; eid += 1
    add(f"#{col_profile_pts}=IFCCARTESIANPOINT((0.15,0.15));")
    add(f"#{col_profile}=IFCRECTANGLEPROFILEDEF(.AREA.,$,#{col_profile_pts},0.3,0.3);")

    # --- Katları bul ---
    stories = sorted(set(el.get("ifc_story", "") for el in elements if el.get("ifc_story")))
    story_elevs = {}
    story_ids = {}

    for i, sname in enumerate(stories):
        elev = i * 3.0
        cp = eid; eid += 1
        ap = eid; eid += 1
        st = eid; eid += 1
        guid = f'STRY{i+1:02d}' + '0' * 18
        add(f"#{cp}=IFCCARTESIANPOINT((0.,0.,{_f(elev)}));")
        add(f"#{ap}=IFCAXIS2PLACEMENT3D(#{cp},#7,#6);")
        add(f"#{st}=IFCBUILDINGSTOREY('{guid}',#5,'{sname}',$,$,#{ap},$,$,.ELEMENT.,{_f(elev)});")
        story_ids[sname] = st
        story_elevs[sname] = elev

    storey_list = ','.join(f'#{v}' for v in story_ids.values())
    add(f"#{eid}=IFCRELAGGREGATES('RA03000000000000000000',#5,$,$,#13,({storey_list}));")
    eid += 1

    rc_members = {s: [] for s in stories}
    beam_conn = connectivity.get("beams", {})
    col_conn = connectivity.get("columns", {})

    for el in elements:
        label = el.get("ifc_name", "")
        story = el.get("ifc_story", "")
        el_type = el.get("ifc_type", "IfcBeam")
        status = el.get("status", "UNMATCHED")
        uc = el.get("unity_check") or 0.0
        fm = el.get("failure_mode", "")
        combo = el.get("governing_combo", "")
        score = el.get("match_score") or 0.0
        guid = el.get("ifc_global_id", f"EL{eid:020d}")

        elev = story_elevs.get(story, 0.)

        # Koordinat hesapla
        x1, y1, z1 = 0., 0., elev
        x2, y2, z2 = 1., 0., elev

        if el_type == "IfcBeam" and label in beam_conn:
            pi = beam_conn[label]["pi"]
            pj = beam_conn[label]["pj"]
            if pi in points and pj in points:
                x1 = points[pi]["x"]; y1 = points[pi]["y"]; z1 = elev + 3.
                x2 = points[pj]["x"]; y2 = points[pj]["y"]; z2 = elev + 3.
        elif el_type == "IfcColumn" and label in col_conn:
            pi = col_conn[label]["pi"]
            if pi in points:
                x1 = points[pi]["x"]; y1 = points[pi]["y"]; z1 = elev
                x2 = points[pi]["x"]; y2 = points[pi]["y"]; z2 = elev + 3.

        length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)
        if length < 0.001:
            length = 1.0

        # Geometry
        p1e = eid; eid += 1
        p2e = eid; eid += 1
        seg = eid; eid += 1
        ax_rep = eid; eid += 1
        ext_place_pt = eid; eid += 1
        ext_place = eid; eid += 1
        ext = eid; eid += 1
        body_rep = eid; eid += 1
        prod_def = eid; eid += 1
        lp_cp = eid; eid += 1
        lp_ap = eid; eid += 1
        lp = eid; eid += 1
        el_e = eid; eid += 1

        add(f"#{p1e}=IFCCARTESIANPOINT((0.,0.,0.));")
        add(f"#{p2e}=IFCCARTESIANPOINT(({_f(length)},0.,0.));")
        add(f"#{seg}=IFCPOLYLINE((#{p1e},#{p2e}));")
        add(f"#{ax_rep}=IFCSHAPEREPRESENTATION(#10,'Axis','Curve3D',(#{seg}));")

        # Extrusion: profil + yön + uzunluk
        add(f"#{ext_place_pt}=IFCCARTESIANPOINT((0.,0.));")
        add(f"#{ext_place}=IFCAXIS2PLACEMENT2D(#{ext_place_pt},#6);")

        if el_type == "IfcColumn":
            add(f"#{ext}=IFCEXTRUDEDAREASOLID(#{col_profile},#9,#7,{_f(length)});")
        else:
            add(f"#{ext}=IFCEXTRUDEDAREASOLID(#{beam_profile},#9,#6,{_f(length)});")

        add(f"#{body_rep}=IFCSHAPEREPRESENTATION(#10,'Body','SweptSolid',(#{ext}));")
        add(f"#{prod_def}=IFCPRODUCTDEFINITIONSHAPE($,$,(#{ax_rep},#{body_rep}));")

        dx = (x2 - x1) / length
        dy = (y2 - y1) / length
        dz = (z2 - z1) / length

        add(f"#{lp_cp}=IFCCARTESIANPOINT(({_f(x1)},{_f(y1)},{_f(z1)}));")
        dir1 = eid; eid += 1
        dir2 = eid; eid += 1
        add(f"#{dir1}=IFCDIRECTION((0.,0.,1.));")
        add(f"#{dir2}=IFCDIRECTION(({_f(dx)},{_f(dy)},{_f(dz)}));")
        add(f"#{lp_ap}=IFCAXIS2PLACEMENT3D(#{lp_cp},#{dir1},#{dir2});")
        add(f"#{lp}=IFCLOCALPLACEMENT($,#{lp_ap});")

        if el_type == "IfcColumn":
            add(f"#{el_e}=IFCCOLUMN('{guid}',#5,'{label}',$,'Column',#{lp},#{prod_def},'{label}');")
        else:
            add(f"#{el_e}=IFCBEAM('{guid}',#5,'{label}',$,'Beam',#{lp},#{prod_def},'{label}');")

        # STAT_Analysis PropertySet
        pv_status = eid; eid += 1
        pv_uc = eid; eid += 1
        pv_fm = eid; eid += 1
        pv_combo = eid; eid += 1
        pv_score = eid; eid += 1
        ps = eid; eid += 1
        rp = eid; eid += 1

        add(f"#{pv_status}=IFCPROPERTYSINGLEVALUE('Status',$,IFCLABEL('{status}'),$);")
        add(f"#{pv_uc}=IFCPROPERTYSINGLEVALUE('UnityCheck',$,IFCREAL({uc}),$);")
        add(f"#{pv_fm}=IFCPROPERTYSINGLEVALUE('FailureMode',$,IFCLABEL('{fm}'),$);")
        add(f"#{pv_combo}=IFCPROPERTYSINGLEVALUE('GoverningCombo',$,IFCLABEL('{combo}'),$);")
        add(f"#{pv_score}=IFCPROPERTYSINGLEVALUE('MatchScore',$,IFCREAL({score}),$);")
        add(f"#{ps}=IFCPROPERTYSET('PS{eid:018d}',#5,'STAT_Analysis',$,(#{pv_status},#{pv_uc},#{pv_fm},#{pv_combo},#{pv_score}));")
        add(f"#{rp}=IFCRELDEFINESBYPROPERTIES('RP{eid:018d}',#5,$,$,(#{el_e}),#{ps});")
        eid += 2

        if story in rc_members:
            rc_members[story].append(el_e)

    # Spatial containment — her kat ayrı
    for i, story in enumerate(stories):
        if rc_members[story]:
            members = ','.join(f'#{e}' for e in rc_members[story])
            st_id = story_ids[story]
            add(f"#{eid}=IFCRELCONTAINEDINSPATIALSTRUCTURE('RC{i:020d}',#5,$,$,({members}),#{st_id});")
            eid += 1

    add("ENDSEC;")
    add("END-ISO-10303-21;")

    return '\n'.join(lines).encode('utf-8')
