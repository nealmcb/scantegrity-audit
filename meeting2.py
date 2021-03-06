"""
The meeting two verification

Usage:
python meeting2.py <DATA_PATH>

data path should NOT have a trailing slash
"""

# core imports
import sys, base64
import base
import data
import filenames

if len(sys.argv) > 2:
  # Note that the path provided as the second argument must be relative to the data directory, not absolute
  filenames.set_meeting_two_random_data(sys.argv[2])

# use the meeting1 data structures too
import meeting1

# pull in certain data structures from meeting1
election, p_table, partitions = meeting1.election, meeting1.p_table, meeting1.partitions

# second meeting
meeting_two_in_xml = base.file_in_dir(base.DATA_PATH, filenames.MEETING_TWO_IN, 'Meeting Two In')
meeting_two_out_xml = base.file_in_dir(base.DATA_PATH, filenames.MEETING_TWO_OUT, "Meeting Two Out")
meeting_two_out_commitments_xml = base.file_in_dir(base.DATA_PATH, filenames.MEETING_TWO_OUT_COMMITMENTS, "Meeting Two Out Commitments")
meeting_two_random_data = base.file_in_dir(base.DATA_PATH, filenames.MEETING_TWO_RANDOM_DATA, "Random Data for Meeting Two Challenges", xml=False, correct_windows=False)

# get the challenges
challenge_p_table = data.PTable()
challenge_p_table.parse(meeting_two_in_xml.find('challenges/print'))

# get the response
response_p_table, response_partitions = data.parse_database(meeting_two_out_xml)

challenge_row_ids = challenge_p_table.rows.keys()

def verify_open_p_and_d_tables(election, committed_p_table, committed_partitions, open_p_table, open_partitions):
  # check P table commitments
  for row in open_p_table.rows.values():
    if not committed_p_table.check_full_row(row, election.constant):
      return False
  
  # Now we go through the partitions, the d tables within each partition,
  # and we look at the rows that are revealed. As we do this, we'll also
  # spot check that the permutations in a given d_table row match the p_table rows revealed
  
  # first we get the partition-and-question map for this election, which
  # is effectively a tree representation of how the questions are grouped
  # in partitions, with each leaf being the number of answers for that given question.
  partition_map = election.partition_map
  
  # the list of p table rows that are opened up
  p_table_row_ids = sorted([r['id'] for r in open_p_table.rows.values()])
  
  # loop through partitions
  for p_id, partition in committed_partitions.iteritems():
    # loop through d tables for that partition
    for d_table_id, d_table in partition.iteritems():
      # get the corresponding response D table
      response_d_table = open_partitions[p_id][d_table_id]
      
      # for efficiency of lookup, so we don't have to look up D-table rows by p-table row ID
      # (which we haven't indexed), we check that
      # (1) the responses are correct according to the commitments
      # (2) the list of p_id rows in each response set matches the challenge row IDs
      
      # (1) reveals match
      for row_id, response_row in response_d_table.rows.iteritems():
        if not d_table.check_full_row(p_id, d_table_id, response_row, election.constant):
          return False
      
      # (2) list of p_ids matches
      if p_table_row_ids != sorted([r['pid'] for r in response_d_table.rows.values()]):
        return False
      
      # (3) permutations
      for row_id, response_row in response_d_table.rows.iteritems():
        # perms contains the d2, d3, and d4 fields, each of which is a list of permutations,
        # so we have a list of lists of permutations
        perms = response_d_table.get_permutations_by_row_id(row_id, partition_map[p_id])
        d_perm_left = [data.Permutation(p) for p in perms[0]]
        d_perm_right = [data.Permutation(p) for p in perms[2]]
        
        p_row_id = response_d_table.rows[row_id]['pid']
        
        # get the corresponding P table permutation subset
        # P also has two permutation fields, each of which is a list of permutations
        # once parsed, an additional layer is inserted, the index by partition_id
        p_perms_full = open_p_table.get_permutations_by_row_id(p_row_id, partition_map)
        p_perm_1 = [data.Permutation(perms) for perms in p_perms_full[0][p_id]]
        p_perm_2 = [data.Permutation(perms) for perms in p_perms_full[1][p_id]]

        # on the d table, just d2 then d4 to go from coded to decoded
        d_composed = data.compose_lists_of_permutations(d_perm_left, d_perm_right)
        
        # the composition of the print tables is p_2 o p_1_inv to go from coded to decoded
        p_composed = data.compose_lists_of_permutations(p_perm_2, [~p for p in p_perm_1])
        
        if d_composed != p_composed:
          return False
  
  # if we make it to here, it's good
  return True

  
# actual meeting two verifications
def verify(output_stream):  
  p_table_permutations = {}
  
  # check the generation of the challenge rows
  # we assume that the length of the challenge list is the right one
  challenge_row_ids_ints = set([int(c) for c in challenge_row_ids])
  challenges_match_randomness = False
  seed = meeting_two_random_data + election.constant
  regenerate_row_ids_ints = set(base.generate_random_int_list(seed, election.num_ballots, len(challenge_row_ids)))

  if challenge_row_ids_ints == regenerate_row_ids_ints:
    challenges_match_randomness = True
  else:
    print "Challenges Don't Match Randomness:"
    print " challenge_row_ids_ints: %s" % challenge_row_ids_ints
    print " generate_random_int_list: %s" % regenerate_row_ids_ints
    print " diff: %s" % (regenerate_row_ids_ints ^ challenge_row_ids_ints)

    import pdb; pdb.set_trace()

  
  # check that the open P table rows match the challenge
  assert sorted(challenge_row_ids) == sorted([r['id'] for r in response_p_table.rows.values()]), "challenges don't match revealed row IDs in P table"
  
  # check that the P and D tables are properly revealed
  assert verify_open_p_and_d_tables(election, p_table, partitions, response_p_table, response_partitions), "bad reveal of P and D tables"
  
  print """Election ID: %s
Meeting 2 Successful

%s ballots challenged and answered successfully.

Challenges Match Randomness? %s

%s
""" % (election.spec.id, len(challenge_row_ids), str(challenges_match_randomness).upper(), base.fingerprint_report())

if __name__ == '__main__':
  verify(sys.stdout)
