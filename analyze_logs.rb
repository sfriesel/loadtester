def show_stats(d, prefix="")
  n = d.size
  puts "#{ prefix }number of entries: #{ n } #"

  avg = d.reduce(:+) / n
  puts "#{ prefix }average: #{ avg } s"

  med = d[n / 2]
  puts "#{ prefix }median: #{ med } s"

  std_dev = (d.reduce(0) { |acc, e| acc + (e - avg) ** 2 } / n) ** 0.5
  puts "#{ prefix }standard deviation: #{ std_dev }"
end


def analyze(d, options={})
  show_stats d
  n = d.size

  if options[:partitions]
    puts "\npartitions:"
    slice_len = (n % 10 == 0) ? n / 10 : n / 10 + 1
    partitions = d.each_slice(slice_len).to_a

    partitions.each_with_index do |p, i|
      puts "\tpartition #{ i*10 }%-#{ (i + 1) * 10 }%"
      show_stats p, "\t\t"
    end
  end

  puts "quantiles:"
  quantiles = [ 0, 1, 2, 5, 10, 25, 50, 75, 90, 95, 98, 99, 100 ]
  quantiles.each { |e| puts "\t#{ e }th: #{ d[ ((n.to_f - 1) / 100 * e).to_i ] } s" }
end


def analyze_file(log_file)
  puts "Statistics for file: #{ log_file }\n\n"
  stat_and_time = open(log_file).readlines.map do |l|
    t = l.split
    [ t[2].to_i, t[1].to_f - t[0].to_f ]
  end

  [1, 0].each do |status|
    puts "For status: #{ status } => #{ (status == 1) ? 'success' : 'error' }"
    puts "=" * 40
    durations = stat_and_time.select { |s, _| s == status }.map { |_, duration| duration }.sort

    analyze durations, :partitions => false rescue puts "NO DATA for this status"

    puts "\n\n"
  end
end


analyze_file ARGV.first