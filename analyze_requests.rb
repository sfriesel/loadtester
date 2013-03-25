require 'set'
require 'binary_search/native'

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

  puts buckets.inspect
end


def analyze_file(req_file)
  puts "Request statistics for file: #{ req_file }\n\n"

  tmp_times = SortedSet.new
  open(req_file).readlines.each do |l|
    t = l.split
    tmp_times.add t[1].to_f
    tmp_times.add t[2].to_f
  end
  times = tmp_times.to_a
  n = times.size
  concurrent_req = (n - 1).times.map { 0 }

  open(req_file).readlines.each do |l|
    t = l.split
    start_time = t[1].to_f
    end_time = t[2].to_f

    min_i = times.binary_index start_time
    max_i = times.binary_index end_time
    min_i.upto(max_i - 1) { |i| concurrent_req[i] += 1 }
  end

  data = concurrent_req.each_index.map do |i|
    [ times[i], times[i + 1], concurrent_req[i] ]
  end

  analyze data
end


analyze_file ARGV.first
