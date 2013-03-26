def show_stats(d, options={})
  n = d.size
  prefix = options[:prefix] || ""
  unit = options[:unit] || ""

  puts "#{ prefix }number of entries: #{ n } #"

  avg = d.reduce(:+) / n
  puts "#{ prefix }average: #{ avg } #{ unit }"

  med = d[n / 2]
  puts "#{ prefix }median: #{ med } #{ unit }"

  std_dev = (d.reduce(0) { |acc, e| acc + (e - avg) ** 2 } / n) ** 0.5
  puts "#{ prefix }standard deviation: #{ std_dev }"
end
