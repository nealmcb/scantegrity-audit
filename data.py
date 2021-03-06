"""
The data abstractions for Scantegrity Audit

ben@adida.net
2009-10-10
"""

import base64
from xml.etree import ElementTree
import commitment

def _compare_positions(element_1, element_2):
  """
  a function to help sort elements that have a position attribute
  misspelled in the spec as 'possition'
  """
  return cmp(int(element_1.attrib['possition']), int(element_2.attrib['possition']))
  
def _compare_id(e1, e2):
  return cmp(int(e1.id), int(e2.id))

def sort_by_id(elements):
  return sorted(elements, _compare_id)
  
##
## Permutations
##

class Permutation(object):
  def __init__(self, array_representation):
    self.__permutation = array_representation
  
  def __getitem__(self, item):
    # if it's a non-position, the permutation doesn't touch it
    if item == -1:
      return -1
    return self.__permutation[item]
    
  def __add__(self, other):
    new_array_rep = [other[i] for i in self.__permutation]
    return Permutation(new_array_rep)
  
  def __invert__(self):
    new_array_rep = [None] * len(self.__permutation)
    for i, value in enumerate(self.__permutation):
      new_array_rep[value] = i
    return Permutation(new_array_rep)    
  
  def __str__(self):
    return str(self.__permutation)
  
  def __eq__(self, other):
    return self.__permutation == other.__permutation
    
  def permute_list(self, lst):
    return [self[e] for e in lst]

def walk_permutation_map(p_map, func, running_data):
  """
  walk a permutation map and apply a func at the leaf, with extra args
  passed and returned along the way
  """
  # this is uglier than it needs to be because of weird Python local variable
  # conflicts with closures
  
  if type(p_map) == list:
    perms = []
    for el in p_map:
      new_perm, running_data = walk_permutation_map(el, func, running_data)
      perms.append(new_perm)
    return perms, running_data
  else:
    return func(p_map, running_data)
  
def split_permutations(concatenated_permutations, partition_map):
  """
  Given concatenated permutations [0 1 2 0 1 0 2 3 1] and a partition_map, i.e. [[2],[3,4]],
  split things up into the appropriate tree structure of permutations: [[[0 1]], [[2 0 1], [0 2 3 1]]]

  This is also used to split the p3 column of the P table and the d3 column of the D table,
  where instead of permutations, we are dealing with actual voter selections of candidates.
  In that case, the partition map should list the max_num_answers, not the total_num_answers.
  """
  
  # a function to extract the permutation when we get to the leaf
  # current_index is the running_data that keeps track of where we are
  # in the tree. Note that this assumes depth-first traversal, without
  # parallelization (likely a safe assumption.)
  def subperm(p_map, current_index):
    new_index = current_index + p_map
    return concatenated_permutations[current_index:new_index], new_index
  
  return walk_permutation_map(partition_map, subperm, 0)[0]
  
def compose_lists_of_permutations(list_of_perms_1, list_of_perms_2):
  """
  two lists of permutations, where corresponding indexes into each need to be composed with one another
  """
  return [perm1_el + list_of_perms_2[i] for i, perm1_el in enumerate(list_of_perms_1)]
    

##
## Verification of Symbols Depending on question type
##

def __remove_minus_one_on(array):
  """
  remove everything after a minus one
  """
  try:
    pos = array.index(-1)
    return array[:pos]
  except:
    return array

def _RANK_verify_symbols(ballot_symbols, p_table_symbols, question):
  mx = question.max_num_answers
  # p_table_symbols_processed = __remove_minus_one_on(p_table_symbols)
  for symbol in ballot_symbols:
    try:
      if p_table_symbols[symbol % mx] != symbol / mx:
        return False
    except:
      import pdb; pdb.set_trace()
      
  # check that the number of symbols that are not -1 is equal to the number of symbols
  if len([p for p in p_table_symbols if p != -1]) != len(ballot_symbols):
    import pdb; pdb.set_trace()
    return False
  
  return True

def _SINGLE_verify_symbols(ballot_symbols, p_table_symbols, question):
  return ballot_symbols == __remove_minus_one_on(p_table_symbols)
  
def _MULTIPLE_verify_symbols(ballot_symbols, p_table_symbols, question):
  #return sorted(ballot_symbols) == sorted(__remove_minus_one_on(p_table_symbols))
  # HACK for now, since we care only about rank
  return True

VERIFY_SYMBOLS = {}
VERIFY_SYMBOLS['rank'] = _RANK_verify_symbols
VERIFY_SYMBOLS['one_answer'] = _SINGLE_verify_symbols
VERIFY_SYMBOLS['multiple_answers'] = _MULTIPLE_verify_symbols

##
## Data Structures
##
  
class PartitionInfo(object):
  """
  Maps a section/question to a partition
  
  A section ID or question ID can be any string, so we'll use dictionaries
  """
  def __init__(self):
    self.sections = {}
    self.partitions = []
    self.id = None
    
  def partition_num(self, section_id, question_id):
    return self.sections[section_id][question_id]
  
  @property
  def num_partitions(self):
    return len(self.partitions)
  
  def parse(self, etree):
    """
    parse from an elementtree.
    """
    self.id = etree.find('electionInfo').attrib['id']
    
    # go through each section
    sections = etree.findall('electionInfo/sections/section')
    for s in sections:
      # add the section by its identifier
      self.sections[s.attrib['id']] = new_section = {}
      
      # find all questions
      questions = s.findall('questions/question')
      for q in questions:
        # add mapping of question to partition n., which is an integer
        new_section[q.attrib['id']] = int(q.attrib['partitionNo'])
    
    # figure out the partitions
    num_partitions = max([max(section.values()) for section in self.sections.values()]) + 1
    
    # set up the partitions as lists of questions within each partition
    self.partitions = [[] for i in range(num_partitions)]
    
    # index the questions by partition
    for s_id, section in self.sections.iteritems():
      for q_id, q_partition in section.iteritems():
        self.partitions[int(q_partition)].append({'section_id': s_id, 'question_id': q_id})
        
    # we're assuming here that the ordering within the partitions is correct
    # because the documentation says nothing more
        
class Question(object):
  """
  A question's answers are represented as a position-ordered list of answer IDs.
  """
  def __init__(self):
    self.id = None
    self.type_answer_choice = None
    self.max_num_answers = None
    self.answers = None
    self.section_id = None
    self.partition_num = None
    self.position_in_partition = None
    
  def parse(self, etree, section_id, partition_info):
    """
    parse the answers
    """
    self.id = etree.attrib['id']
    self.position = int(etree.attrib['possition'])
    self.type_answer_choice = etree.attrib['typeOfAnswerChoice']
    self.max_num_answers = int(etree.attrib['max_number_of_answers_selected'])
    
    self.answers = etree.findall('answers/answer')
    self.answers.sort(_compare_positions)
    
    self.section_id = section_id
    self.partition_num = partition_info.partition_num(self.section_id, self.id)

class ElectionSpec(object):
  """
  Each section is a list of position-ordered questions
  
  parse from an electionspec.xml file
  """
  
  def __init__(self, partition_info):
    self.partition_info = partition_info
    self.sections = {}
    
    # a linear list of all the questions, when the sections don't matter
    self.questions = []
    self.questions_by_id = {}
    
    # a list of questions by partition
    self.questions_by_partition = []
    
  def lookup_question(self, section_id, question_id):
    return self.sections[section_id][question_id]
  
  def lookup_question_from_partition_info(self, q_info):
    return self.lookup_question(self, q_info['section_id'], q_info['question_id'])
  
  def parse(self, etree):
    self.id = etree.find('electionInfo').attrib['id']

    # check match of election IDs
    if self.partition_info and self.partition_info.id != self.id:
      import pdb; pdb.set_trace()
      raise Exception("election IDs don't match")
    
    # initialize the questions_by_partition
    self.questions_by_partition = [[] for i in range(self.partition_info.num_partitions)]
    
    # go through each section
    sections = etree.findall('electionInfo/sections/section')
    for s in sections:
      # add the section by its identifier
      self.sections[s.attrib['id']] = new_section = {}
      
      questions = s.findall('questions/question')
      
      # sort them by "possition"
      questions.sort(_compare_positions)
      
      # go through the questions, create question object
      for q in questions:
        q_object= Question()
        q_object.parse(q, s.attrib['id'], self.partition_info)
        
        q_object.position_in_partition = len(self.questions_by_partition[q_object.partition_num])
        
        new_section[q.attrib['id']] = q_object
        self.questions.append(q_object)
        self.questions_by_partition[q_object.partition_num].append(q_object)
        self.questions_by_id[q_object.id] = q_object
    
    
class Election(object):
  def __init__(self, election_spec):
    self.num_d_tables = 0
    self.num_ballots = 0
    self.constant = None
    self.spec = election_spec
    
  @property
  def partition_map(self):
    # list of lists of dictionaries, each dictionary contains the question and section IDs
    partitions = self.spec.partition_info.partitions
    
    # look up the number of answers for each question within each section
    return [[len(self.spec.sections[q_info['section_id']][q_info['question_id']].answers) for q_info in partition] for partition in partitions]

  @property
  def partition_map_choices(self):
    """
    same as partition map, only with the max num of selected answers for each question,
    rather than the total num of answers to choose from. Useful for parsing the voter selection.
    """
    # list of lists of dictionaries, each dictionary contains the question and section IDs
    partitions = self.spec.partition_info.partitions

    # look up the number of answers for each question within each section
    return [[self.spec.sections[q_info['section_id']][q_info['question_id']].max_num_answers for q_info in partition] for partition in partitions]

  @property
  def num_partitions(self):
    """
    A list of partition IDs
    """
    return len(self.spec.partition_info.partitions)
  
  def questions_in_partition(self, partition_num):
    """
    list of question objects in a given partition
    """
    return self.spec.questions_by_partition[partition_num]
    
  def parse(self, etree):
    """
    parse from the MeetingOneIn file
    """
    self.num_d_tables = int(etree.findtext('noDs'))
    self.num_ballots = int(etree.findtext('noBallots'))
    self.constant = base64.decodestring(etree.findtext('constant'))

class Table(object):
  """
  A base table class that has features that P, D, and R tables all need
  """
  
  # fields that are to be interpreted as permutations
  PERMUTATION_FIELDS = []
  INTEGER_FIELDS = ['id']
  
  def __init__(self):
    self.id = None
    self.rows = {}
    self.__permutations_by_row_id = {}
    
  @classmethod
  def process_row(cls, row):
    """
    for the fields that are interpreted as permutations,
    do proper splitting on spaces to create python lists
    """
    for f in cls.PERMUTATION_FIELDS:
      if row.has_key(f):
        row[f] = [int(el) for el in row[f].split(' ')]
    
    return row

  def get_permutations_by_row_id(self, row_id, pmap):
    # already computed?
    if not self.__permutations_by_row_id.has_key(row_id):
      self.__permutations_by_row_id[row_id] = new_row = []
      for perm_field in self.PERMUTATION_FIELDS:
        if self.rows[row_id].has_key(perm_field):
          new_row.append(split_permutations(self.rows[row_id][perm_field], pmap))
        else:
          new_row.append(None)

    return self.__permutations_by_row_id[row_id]
    
  def parse(self, etree):
    if etree.attrib.has_key('id'):
      self.id = int(etree.attrib['id'])
    
    # look for all rows
    for row_el in etree.findall('row'):
      self.rows[int(row_el.attrib['id'])] = new_row = self.process_row(row_el.attrib)      
      
      # convert fields to ints when it matters
      for k in self.INTEGER_FIELDS:
        if new_row.has_key(k):
          new_row[k] = int(new_row[k])
  
class PTable(Table):
  PERMUTATION_FIELDS = ['p1', 'p2', 'p3']
      
  @classmethod
  def __check_commitment(cls, commitment_str, row_id, permutation, salt, constant):
    """
    check the reveal of a commitment to a permutation,
    """
    # prepare the string that we are committing to
    message = str(row_id)
    message += ''.join([chr(el) for el in permutation])

    # reperform commitment and check equality
    return commitment_str == commitment.commit(message, salt, constant)
    
  def check_c1(self, reveal_row, constant):
    return self.__check_commitment(self.rows[reveal_row['id']]['c1'], reveal_row['id'], reveal_row['p1'], reveal_row['s1'], constant)
  
  def check_c2(self, reveal_row, constant):
    return self.__check_commitment(self.rows[reveal_row['id']]['c2'], reveal_row['id'], reveal_row['p2'], reveal_row['s2'], constant)
    
  def check_full_row(self, reveal_row, constant):
    return self.check_c1(reveal_row, constant) and self.check_c2(reveal_row, constant)
    

class DTable(Table):
  PERMUTATION_FIELDS = ['d2', 'd3', 'd4']
  INTEGER_FIELDS = ['id', 'pid', 'rid']

  @classmethod
  def __check_commitment(cls, commitment_str, partition_id, instance_id, row_id, external_id, permutation, salt, constant):
    """
    check the reveal of a commitment to a permutation,
    the "external_id" is the reference to the other table, either pid or rid
    """
    # prepare the string that we are committing to
    message = chr(partition_id) + chr(instance_id) + str(row_id) + str(external_id)
    message += ''.join([chr(el) for el in permutation])

    # reperform commitment and check equality
    return commitment_str == commitment.commit(message, salt, constant)
  
  def check_cl(self, partition_id, instance_id, reveal_row, constant):
    relevant_row = self.rows[reveal_row['id']]
    return self.__check_commitment(relevant_row['cl'], partition_id, instance_id, relevant_row['id'], reveal_row['pid'], reveal_row['d2'], reveal_row['sl'], constant)

  def check_cr(self, partition_id, instance_id, reveal_row, constant):
    relevant_row = self.rows[reveal_row['id']]
    return self.__check_commitment(relevant_row['cr'], partition_id, instance_id, relevant_row['id'], reveal_row['rid'], reveal_row['d4'], reveal_row['sr'], constant)
    
  def check_full_row(self, *args):
    return self.check_cl(*args) and self.check_cr(*args)
  
class RTable(Table):
  PERMUTATION_FIELDS = ['r']
  
class Ballot(object):
  """
  represents the printed ballot information, with commitments and confirmation codes
  """
  INTEGER_FIELDS = ['pid']
  
  def __init__(self, etree=None):    
    # dictionary of questions, each is a dictionary of symbols
    self.questions = {}
    
    if etree:
      self.parse(etree)
  
  def verify_encodings(self, election, p_table):
    """
    assumes this ballot has open symbols, and check that these symbols correspond
    to the p_table row. Depends on the type of question (rank or otherwise), thus
    the need for the election data structure.
    """
    # going for p3, so it's index 2
    encoded_choices = p_table.get_permutations_by_row_id(self.pid, election.partition_map_choices)[2]
    
    # go through the questions in this ballot
    for q_id, question in self.questions.iteritems():
      ballot_symbols = question.keys()
      q_info = election.spec.questions_by_id[q_id]
      p_table_symbols = encoded_choices[q_info.partition_num][q_info.position_in_partition]

      # go through the symbols and check them:
      for symbol in ballot_symbols:
        if not VERIFY_SYMBOLS[q_info.type_answer_choice](ballot_symbols, p_table_symbols, q_info):
          import pdb;pdb.set_trace()
          return False
              
    return True          
    
  def verify_code_openings(self, open_ballot, constant, code_callback_func = None):
    """
    this ballot is the commitment, the other ballot is the opening.
    
    The code_callback_func, if present, is a function to call back:
    code_callback_func(web_serial_num, pid, question_id, symbol_id, confirmation_code)
    
    This is called only when a code is successfully verified, and enables bookkeeping of
    codes to show the voters in a verification interface.
    """
    
    # pid match
    if self.pid != open_ballot.pid:
      return False
    
    # check opening of barcode serial number if it's there
    if hasattr(open_ballot, 'barcodeSerial') and open_ballot.barcodeSerial != None:
      if self.barcodeSerialCommitment != commitment.commit(str(self.pid) + " " + open_ballot.barcodeSerial, open_ballot.barcodeSerialSalt, constant):
        return false
        
    # check opening of web serial number
    if self.webSerialCommitment != commitment.commit(str(self.pid) + " " + open_ballot.webSerial, open_ballot.webSerialSalt, constant):
      return False
    
    # check opening of all marked codes
    for q_id, q in open_ballot.questions.iteritems():
      # the symbols for this ballot
      committed_symbols = self.questions[q_id]
      
      # go through the open symbols
      for s_id, s in q.iteritems():
        if committed_symbols[s_id]['c'] != commitment.commit(" ".join([str(self.pid), q_id, str(s_id), s['code']]), s['salt'], constant):
          return False
          
        # record the code for this ballot
        if code_callback_func:
          code_callback_func(open_ballot.webSerial, self.pid, q_id, s_id, s['code'])          
  
    # only if all tests pass, then succeed
    return True
    
  def parse(self, etree):
    # add all of the attributes
    self.__dict__.update(etree.attrib)
    
    for k in self.INTEGER_FIELDS:
      self.__dict__[k] = int(self.__dict__[k])
    
    for q_el in etree.findall('question'):
      self.questions[q_el.attrib['id']] = new_q = {}
      
      for symbol_el in q_el.findall('symbol'):
        new_q[int(symbol_el.attrib['id'])] = symbol_el.attrib

##
## some reusable utilities
##

def parse_p_table(etree, path='database/print'):
  # the P table
  p_table = PTable()
  p_table.parse(etree.find(path))
  
  return p_table

def parse_d_tables(etree, path='database/partition'):
  # the multiple D tables by partition
  partitions = {}
  partition_elements = etree.findall(path)
  
  # go through each partition, each one is a dictionary of D-Table instances keyed by ID
  for partition_el in partition_elements:
    partitions[int(partition_el.attrib['id'])] = new_partition = {}

    d_table_instances = partition_el.findall('decrypt/instance')
    for d_table_el in d_table_instances:
      new_partition[int(d_table_el.attrib['id'])] = new_d_table = DTable()
      new_d_table.parse(d_table_el)

  return partitions

def parse_r_tables(etree, path='database/partition'):
  # the multiple D tables by partition
  partitions = {}
  partition_elements = etree.findall(path)
  
  # go through each partition, each one is a dictionary of D-Table instances keyed by ID
  for partition_el in partition_elements:
    r_table_el = partition_el.find('results')
    r_table = RTable()
    r_table.parse(r_table_el)
    
    partitions[int(partition_el.attrib['id'])] = r_table

  return partitions
  
def parse_database(etree):
  """
  parses a P table and a bunch of D tables, which happens a few times
  
  The partition_id and instance_id are integers
  """
  
  p_table = parse_p_table(etree)
  partitions = parse_d_tables(etree)
      
  return p_table, partitions

def parse_ballot_table(etree):
  # the ballots
  ballot_elements = etree.findall('database/printCommitments/ballot')
  
  return dict([(b.pid, b) for b in [Ballot(e) for e in ballot_elements]])
  
