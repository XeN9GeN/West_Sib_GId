import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shapely.geometry import shape

from scripts import import_osm
from scripts import import_osm_pbf


class OSMImportPBFTests(unittest.TestCase):
    def test_node_feature_uses_coordinates_expected_by_database_importer(self):
        feature = {
            "type": "Feature",
            "properties": {
                "@type": "node",
                "@id": 176389851,
                "historic": "memorial",
                "name": "Test memorial",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [73.368, 54.99],
            },
        }

        element = import_osm_pbf.feature_to_osm_element(feature)
        row = import_osm.to_poi_row(element)

        self.assertEqual(element["lon"], 73.368)
        self.assertEqual(element["lat"], 54.99)
        self.assertEqual(row["osm_type"], "node")
        self.assertEqual(row["osm_id"], 176389851)

    def test_concave_polygon_feature_uses_point_inside_geometry(self):
        feature = {
            "type": "Feature",
            "properties": {
                "@type": "way",
                "@id": 123,
                "historic": "monument",
                "name": "Test monument",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [70.0, 51.0],
                    [73.0, 51.0],
                    [73.0, 54.0],
                    [72.0, 54.0],
                    [72.0, 52.0],
                    [71.0, 52.0],
                    [71.0, 54.0],
                    [70.0, 54.0],
                    [70.0, 51.0],
                ]],
            },
        }

        element = import_osm_pbf.feature_to_osm_element(feature)

        self.assertEqual(element["type"], "way")
        self.assertEqual(element["id"], 123)
        self.assertEqual(element["tags"], {
            "historic": "monument",
            "name": "Test monument",
        })
        point = shape(feature["geometry"]).representative_point()
        self.assertTrue(shape(feature["geometry"]).covers(point))
        self.assertEqual(element["center"], {"lon": point.x, "lat": point.y})

    def test_unparseable_multipolygon_falls_back_to_coordinate_bounds(self):
        feature = {
            "type": "Feature",
            "properties": {
                "@type": "relation",
                "@id": 456,
                "historic": "monument",
            },
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [[[70.0, 51.0], [72.0, 51.0], [72.0, 53.0], [70.0, 51.0]]],
                    [[[80.0, 55.0], [82.0, 55.0], [82.0, 57.0], [80.0, 55.0]]],
                ],
            },
        }

        with patch.object(
            import_osm_pbf,
            "shape",
            side_effect=TypeError("invalid multipolygon coordinates"),
        ):
            element = import_osm_pbf.feature_to_osm_element(feature)

        self.assertEqual(
            element["center"],
            {"lon": 76.0, "lat": 54.0},
        )

    def test_download_resumes_partial_extract(self):
        class PartialResponse(io.BytesIO):
            status = 206
            headers = {
                "Content-Length": "2",
                "Content-Range": "bytes 2-3/4",
            }

            def getcode(self):
                return self.status

        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "extract.osm.pbf"
            partial_path = destination.with_suffix(destination.suffix + ".part")
            partial_path.write_bytes(b"ab")

            with patch.object(
                import_osm_pbf,
                "urlopen",
                return_value=PartialResponse(b"cd"),
            ) as urlopen_mock:
                result = import_osm_pbf.download_extract(
                    "https://example.test/extract.osm.pbf",
                    destination,
                )

                self.assertEqual(result.read_bytes(), b"abcd")
                self.assertEqual(
                    urlopen_mock.call_args.args[0].get_header("Range"),
                    "bytes=2-",
                )

    def test_download_retries_read_timeout_from_saved_offset(self):
        class InterruptedResponse(io.BytesIO):
            status = 200
            headers = {"Content-Length": "4"}

            def __init__(self):
                super().__init__()
                self.read_count = 0

            def getcode(self):
                return self.status

            def read(self, size=-1):
                self.read_count += 1
                if self.read_count == 1:
                    return b"ab"
                raise TimeoutError("read timed out")

        class ResumedResponse(io.BytesIO):
            status = 206
            headers = {
                "Content-Length": "2",
                "Content-Range": "bytes 2-3/4",
            }

            def getcode(self):
                return self.status

        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "extract.osm.pbf"
            with patch.object(
                import_osm_pbf,
                "urlopen",
                side_effect=[InterruptedResponse(), ResumedResponse(b"cd")],
            ) as urlopen_mock, patch.object(import_osm_pbf.time, "sleep") as sleep_mock:
                result = import_osm_pbf.download_extract(
                    "https://example.test/extract.osm.pbf",
                    destination,
                )

            self.assertEqual(result.read_bytes(), b"abcd")
            self.assertEqual(urlopen_mock.call_count, 2)
            self.assertEqual(
                urlopen_mock.call_args_list[1].args[0].get_header("Range"),
                "bytes=2-",
            )
            sleep_mock.assert_called_once_with(
                import_osm_pbf.DOWNLOAD_RETRY_DELAY_SECONDS
            )


if __name__ == "__main__":
    unittest.main()
