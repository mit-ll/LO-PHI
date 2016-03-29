"""
    Defines a set of document formats.

    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import datetime
import hashlib
import os

# LO-PHI Automation
import lophi_automation.database.utils as utils

DELIMITER = '_'


def analysis_doc_uid(analyzer_name, analyzer_version, sample_uid):
    """
    Returns a string representing the UID of an analysis document for
    a particular analyzer and sample.

    :param analyzer_name: Name of analyzer.
    :type analyzer_name: str
    :param analyzer_version: Version of analyzer.
    :type analyzer_version: int
    :param sample_uid: UID for the sample under analysis.
    :type sample_uid: str

    :returns: str -- the UID of analysis document for sample
    """
    return DELIMITER.join(['analysis', analyzer_name,
                           str(analyzer_version), sample_uid])


def analysis_doc(analyzer_name, analyzer_version, sample_id, machine_str,
                 results_dict, exception=None):
    """
    Returns a dictionary representing an analysis document.

    :param analyzer_name: Name of analyzer generating the document.
    :type analyzer_name: str
    :param analyzer_version: Version of analyzer generating the document.
    :type analyzer_version: int
    :param analyzer_doc_uid: UID for the analysis document.
    :type analyzer_doc_uid: str
    :param sample_uid: UID for the sample under analysis.
    :type sample_uid: str
    :param results_dict: Dictionary of analysis results.
    :type results_dict: dict
    :param exception: String representing any exception that occured.
    :type exception: str

    :returns: dict -- analysis document
    """
    curr_time = datetime.datetime.utcnow()
    adoc = {
        '_id': analysis_doc_uid(analyzer_name, analyzer_version, sample_id),
        'type': 'analysis',
        'time': {'year': curr_time.year,
                 'month': curr_time.month,
                 'day': curr_time.day,
                 'iso': curr_time.isoformat()
                 },
        'analyzer': {'name': analyzer_name, 'version': analyzer_version},
        'machine': machine_str,
        'results': results_dict,
        'exception': exception,
        'sample': sample_id
    }
    return adoc


def _calculate_link_hash(links):
    """
    Creates a hash based on the keys of the links. The names of link
    documents will collide when the source, type, and keyspace of the links
    are the same.
    """
    to_hash = ''.join(sorted(links.keys()))
    # Hashlib takes encoded Strings, not Unicode objects
    return hashlib.md5(to_hash.encode('utf-8')).hexdigest()


known_link_types = ['origin', 'unpacks_to']


def link_doc_id(link_source, link_type, links):
    if link_type not in known_link_types:
        raise RuntimeError("%s unknown link type. Known: %s." % \
                           (link_type, str(known_link_types)))

    if not isinstance(links, dict):
        raise RuntimeError("Links are not dictionary.")

    link_hash = _calculate_link_hash(links)
    return DELIMITER.join(['link', link_type, link_source, link_hash])


def link_doc(link_source, link_type, links):
    """
    Returns a dictionary representing an link document.

    :param link_source: Source of the links (data source, unpacker, etc).
    :type link_source: str
    :param link_type: Type of link document (origin, unpacks_to, etc).
    :type link_type: str
    :param links: Dict of links, corresponding to single provenance graph edges.
                  Key/value semantics for link derivation are defined per link type.
    :type links: dict

    :returns: dict -- link document
    """
    ldoc_id = link_doc_id(link_source, link_type, links)
    curr_time = datetime.datetime.utcnow()
    ldoc = {
        '_id': ldoc_id,
        'type': 'link',
        'time': {'year': curr_time.year,
                 'month': curr_time.month,
                 'day': curr_time.day,
                 'iso': curr_time.isoformat()
                 },
        'source': link_source,
        'link_type': link_type,
        'links': links
    }
    return ldoc


def link_origin_doc(link_source, links, redistribution='none', zip_file=None):
    """
    Returns a dictionary representing a link origin document

    :param link_source: Source of the links (data source, unpacker, etc).
    :type link_source: str
    :param links: Dict of links, corresponding to single provenance graph edges.
                  Key/value semantics for link derivation are:
                       sample_id -> origin_file
    :type links: dict

    :returns: dict -- link document
    """
    ldoc = link_doc(link_source, 'origin', links)
    ldoc['redistribution'] = redistribution
    if zip_file:
        ldoc['zip_file'] = zip_file
    return ldoc


def sample_doc_id(uid):
    return DELIMITER.join(['sample', uid])


def sample_doc(file_path, file_doc_id, redistribution="none"):
    """
    Returns a dictionary representing a file document

    :param file_path: Path to the sample file.
    :type file_path: str
    :param file_doc_id: File doc id as returned by the upload file db command.
    "type file_doc_id: str
    :param metadata: Dictionary with additional information about the file.
    :type metadata: dict

    :returns: dict -- file document
    """
    uid = utils.calculate_combined_hash(file_path)
    doc_id = sample_doc_id(uid)
    return {'_id': doc_id,
            'uid': uid,
            'file_doc_id': file_doc_id,
            'sample': doc_id,
            'type': 'sample',
            'size': os.path.getsize(file_path),
            'md5': utils.calculate_md5(file_path),
            'sha1': utils.calculate_sha1(file_path),
            'sha256': utils.calculate_sha256(file_path),
            'sha512': utils.calculate_sha512(file_path),
            'first_uploaded': str(datetime.datetime.now()),
            'redistribution': redistribution,
            'original filename': os.path.basename(file_path)
            }


def file_doc_id(file_path):
    return DELIMITER.join(['file', utils.calculate_sha256(file_path)])
