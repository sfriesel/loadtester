require 'set'
require 'binary_search/native'

require_relative 'analyze_helpers'

BUCKET_SIZE = 0.1


def next_bucket(n)
  n += 1 
  b_s = n * BUCKET_SIZE
  b_e = (n + 1) * BUCKET_SIZE
  return n, b_s, b_e
end


def analyze(data)
  max_time = data[-1][1]
  buckets = (max_time / BUCKET_SIZE).ceil.times.map { 0 }

  b_n = 0
  data.each do |s, e, x|
    b_s = b_n * BUCKET_SIZE
    b_e = (b_n + 1) * BUCKET_SIZE

    b_n, b_s, b_e = next_bucket b_n while s >= b_e

    if e <= b_e
      buckets[b_n] += (e - s) / BUCKET_SIZE * x
    else
      while b_e <= e
        buckets[b_n] += (b_e - s) / BUCKET_SIZE * x
        b_n, b_s, b_e = next_bucket b_n
        s = b_s
      end
    end
  end

  show_stats buckets, "\t"
end


def extract_times(req_file)
  tmp_times = SortedSet.new
  open(req_file).readlines.each do |l|
    t = l.split
    tmp_times.add t[1].to_f
    tmp_times.add t[2].to_f
  end
  return tmp_times.to_a
end


def calculate_concurent_req(req_file, times)
  concurrent_req = (times.size - 1).times.map { 0 }
  open(req_file).readlines.each do |l|
    t = l.split
    start_time = t[1].to_f
    end_time = t[2].to_f

    min_i = times.binary_index start_time
    max_i = times.binary_index end_time
    min_i.upto(max_i - 1) { |i| concurrent_req[i] += 1 }
  end

  return concurrent_req
end


def analyze_file(req_file, options={})
  puts "Request statistics for file: #{ req_file }"

  times = extract_times req_file
  concurrent_req = calculate_concurent_req(req_file, times)

  data = concurrent_req.each_index.map do |i|
    [ times[i], times[i + 1], concurrent_req[i] ]
  end

  if options[:output]
    f = open options[:output], 'w'
    data.each { |e| f.write "#{ e[0] } #{ e[2] }\n" }
    f.close
  end

  analyze data
end


if ARGV.size == 2
  analyze_file ARGV[0], :output => ARGV[1]
else
  analyze_file ARGV.first
end
